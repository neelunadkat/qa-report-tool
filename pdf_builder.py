"""
pdf_builder.py
──────────────
Builds the full 4-page Quality Circle PDF report using ReportLab.
Called by generate_report.py with the aggregated stats dict.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Flowable
)
from datetime import date

from classifier import CATEGORY_META

W, H   = A4
MARGIN = 18 * mm


# ── COLORS ──────────────────────────────────────────────────────────────────────
C_DARK        = colors.HexColor('#1A1A1A')
C_MUTED       = colors.HexColor('#6B6B6B')
C_LIGHT_GRAY  = colors.HexColor('#F5F5F3')
C_BORDER      = colors.HexColor('#E0DED8')
C_WHITE       = colors.white
C_BLUE        = colors.HexColor('#185FA5')
C_BLUE_LIGHT  = colors.HexColor('#E6F1FB')
C_TEAL        = colors.HexColor('#0F6E56')
C_TEAL_LIGHT  = colors.HexColor('#E1F5EE')
C_CORAL       = colors.HexColor('#993C1D')
C_CORAL_LIGHT = colors.HexColor('#FAECE7')
C_AMBER       = colors.HexColor('#854F0B')
C_AMBER_LIGHT = colors.HexColor('#FAEEDA')
C_PURPLE      = colors.HexColor('#534AB7')
C_PURPLE_LIGHT= colors.HexColor('#EEEDFE')
C_GRAY_MED    = colors.HexColor('#888780')


def hex_to_color(h): return colors.HexColor(h)


# ── STYLES ───────────────────────────────────────────────────────────────────────
def make_styles():
    return {
        'cover_title':   ParagraphStyle('cover_title',   fontName='Helvetica-Bold',  fontSize=28, leading=34, textColor=C_DARK,  spaceAfter=6),
        'cover_sub':     ParagraphStyle('cover_sub',     fontName='Helvetica',        fontSize=13, leading=18, textColor=C_MUTED, spaceAfter=4),
        'cover_meta':    ParagraphStyle('cover_meta',    fontName='Helvetica',        fontSize=10, leading=14, textColor=C_MUTED),
        'section_label': ParagraphStyle('section_label', fontName='Helvetica-Bold',  fontSize=8,  leading=11, textColor=C_MUTED, spaceBefore=16, spaceAfter=6, letterSpacing=1.2),
        'h2':            ParagraphStyle('h2',            fontName='Helvetica-Bold',  fontSize=14, leading=18, textColor=C_DARK,  spaceBefore=2,  spaceAfter=4),
        'body':          ParagraphStyle('body',          fontName='Helvetica',        fontSize=10, leading=14, textColor=C_DARK,  spaceAfter=6),
        'body_muted':    ParagraphStyle('body_muted',    fontName='Helvetica',        fontSize=9,  leading=13, textColor=C_MUTED, spaceAfter=4),
        'small':         ParagraphStyle('small',         fontName='Helvetica',        fontSize=8,  leading=11, textColor=C_MUTED),
        'footer_style':  ParagraphStyle('footer_style',  fontName='Helvetica',        fontSize=7.5,leading=10, textColor=C_MUTED, alignment=TA_CENTER),
    }


# ── CUSTOM FLOWABLES ─────────────────────────────────────────────────────────────
class ColorHR(Flowable):
    def __init__(self, color=C_BORDER, thickness=0.5):
        self.color = color; self.thickness = thickness
        self.width = 0; self.height = self.thickness + 3

    def wrap(self, avail_w, avail_h):
        self.width = avail_w
        return self.width, self.height

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, self.thickness / 2, self.width, self.thickness / 2)


class HorizBarChart(Flowable):
    """Horizontal bar chart for category totals."""
    def __init__(self, data, bar_colors, height=150):
        self.data       = data          # [(label, value, pct_str), ...]
        self.bar_colors = bar_colors
        self.height     = height
        self.width      = 0

    def wrap(self, avail_w, avail_h):
        self.width = avail_w
        return self.width, self.height

    def draw(self):
        c        = self.canv
        max_val  = max(d[1] for d in self.data) or 1
        label_w  = 95
        num_w    = 50
        bar_area = self.width - label_w - num_w
        row_h    = self.height / len(self.data)
        bar_h    = min(row_h * 0.42, 13)

        for i, (label, val, pct) in enumerate(self.data):
            y     = self.height - (i + 1) * row_h + row_h * 0.28
            bar_w = (val / max_val) * bar_area

            c.setFont('Helvetica', 8)
            c.setFillColor(C_DARK)
            c.drawString(0, y + bar_h / 2 - 3.5, label)

            c.setFillColor(C_LIGHT_GRAY)
            c.roundRect(label_w, y, bar_area, bar_h, 2, stroke=0, fill=1)

            c.setFillColor(self.bar_colors[i])
            if bar_w > 2:
                c.roundRect(label_w, y, bar_w, bar_h, 2, stroke=0, fill=1)

            c.setFont('Helvetica-Bold', 8)
            c.setFillColor(C_DARK)
            c.drawString(label_w + bar_area + 6, y + bar_h / 2 - 3.5, f"{val}  ({pct})")


class StackedBarChart(Flowable):
    """Stacked bar chart: Developer / Designer / Both per category."""
    def __init__(self, data, legend, height=150):
        self.data    = data      # [(label, {Developer:n, Designer:n, Both:n}), ...]
        self.legend  = legend    # [(key, hex_color), ...]
        self.height  = height
        self.width   = 0

    def wrap(self, avail_w, avail_h):
        self.width = avail_w
        return self.width, self.height + 20

    def draw(self):
        c        = self.canv
        label_w  = 95
        bar_area = self.width - label_w - 35
        row_h    = self.height / len(self.data)
        bar_h    = min(row_h * 0.42, 13)
        max_val  = max(sum(d[1].values()) for d in self.data) or 1

        # Legend
        lx = label_w
        for key, col in self.legend:
            c.setFillColor(hex_to_color(col))
            c.rect(lx, self.height + 7, 8, 8, stroke=0, fill=1)
            c.setFillColor(C_DARK)
            c.setFont('Helvetica', 7.5)
            c.drawString(lx + 11, self.height + 8, key)
            lx += 68

        for i, (label, vals) in enumerate(self.data):
            y     = self.height - (i + 1) * row_h + row_h * 0.28
            total = sum(vals.values())

            c.setFont('Helvetica', 8)
            c.setFillColor(C_DARK)
            c.drawString(0, y + bar_h / 2 - 3.5, label)

            c.setFillColor(C_LIGHT_GRAY)
            c.roundRect(label_w, y, bar_area, bar_h, 2, stroke=0, fill=1)

            x_off = 0
            for key, col in self.legend:
                v     = vals.get(key, 0)
                seg_w = (v / max_val) * bar_area
                if seg_w > 1:
                    c.setFillColor(hex_to_color(col))
                    c.rect(label_w + x_off, y, seg_w, bar_h, stroke=0, fill=1)
                x_off += seg_w

            c.setFont('Helvetica-Bold', 8)
            c.setFillColor(C_DARK)
            c.drawString(label_w + bar_area + 6, y + bar_h / 2 - 3.5, str(total))


# ── PAGE CALLBACKS ────────────────────────────────────────────────────────────────
def _on_page(project_name, today_str):
    def fn(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(C_BLUE)
        canvas.rect(0, H - 5, W, 5, stroke=0, fill=1)
        canvas.setFont('Helvetica', 7.5)
        canvas.setFillColor(C_MUTED)
        canvas.drawCentredString(
            W / 2, 9 * mm,
            f"{project_name}  —  Quality Circle QA Report  |  Encircle Technologies  |  {today_str}  |  Page {doc.page}"
        )
        canvas.restoreState()
    return fn


# ── MAIN BUILD FUNCTION ───────────────────────────────────────────────────────────
def build_pdf(project_name: str, stats: dict, out_path: str):
    """
    Args:
        project_name: Name of the Google Sheet / project
        stats: Dict returned by aggregate() in generate_report.py
        out_path: Where to save the PDF
    """
    S      = make_styles()
    today  = date.today().strftime("%B %d, %Y")
    cw     = W - 2 * MARGIN

    doc = SimpleDocTemplate(
        out_path, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=22 * mm, bottomMargin=20 * mm
    )

    story = []

    # ── Extract stats ──────────────────────────────────────────────────────────
    total      = stats['total']
    dev_cnt    = stats['developer']
    des_cnt    = stats['designer']
    both_cnt   = stats['both']
    by_type    = stats['by_type']
    by_page    = stats['by_page']
    reviewed   = stats['reviewed_df']

    dev_pct    = round(dev_cnt  / total * 100, 1) if total else 0
    des_pct    = round(des_cnt  / total * 100, 1) if total else 0
    both_pct   = round(both_cnt / total * 100, 1) if total else 0

    # ── PAGE 1: COVER ──────────────────────────────────────────────────────────
    story.append(Spacer(1, 16 * mm))
    story.append(Paragraph('Quality Circle', S['cover_sub']))
    story.append(Paragraph('Issue Analysis Report', S['cover_title']))
    story.append(ColorHR(C_BLUE, 2))
    story.append(Spacer(1, 5))
    story.append(Paragraph(f'Project: <b>{project_name}</b>  &nbsp;·&nbsp;  Sheet: Quality Circle  &nbsp;·&nbsp;  Filter: Status = REVIEWED', S['cover_meta']))
    story.append(Paragraph(f'Prepared by: QA Team Lead  &nbsp;·&nbsp;  Encircle Technologies  &nbsp;·&nbsp;  {today}', S['cover_meta']))
    story.append(Spacer(1, 10 * mm))

    # Metric cards
    labels     = ['Total Reviewed', 'Developer Issues', 'Designer Issues', 'Both Issues']
    values     = [str(total), str(dev_cnt), str(des_cnt), str(both_cnt)]
    pcts       = ['', f'{dev_pct}%', f'{des_pct}%', f'{both_pct}%']
    met_colors = [C_BLUE, C_TEAL, C_CORAL, C_AMBER]

    cells = []
    for lbl, val, pct, col in zip(labels, values, pcts, met_colors):
        rows = [
            [Paragraph(val, ParagraphStyle('mn', fontName='Helvetica-Bold', fontSize=24, leading=28, textColor=col, alignment=TA_CENTER))],
            [Paragraph(lbl, ParagraphStyle('ml', fontName='Helvetica', fontSize=8, leading=10, textColor=C_MUTED, alignment=TA_CENTER))],
        ]
        if pct:
            rows.append([Paragraph(pct, ParagraphStyle('mp', fontName='Helvetica-Bold', fontSize=9, leading=11, textColor=col, alignment=TA_CENTER))])
        t = Table(rows, colWidths=[cw / 4 - 4])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), C_LIGHT_GRAY),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ]))
        cells.append(t)

    metric_tbl = Table([cells], colWidths=[cw / 4] * 4)
    metric_tbl.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(metric_tbl)
    story.append(Spacer(1, 8 * mm))

    # Executive summary
    exec_text = (
        f'This report covers <b>{total} REVIEWED issues</b> identified across '
        f'{len(by_page)} pages in the <b>{project_name}</b> Quality Circle sheet. '
        f'Issues are categorised by type (UI/UX, Functional, Image/Visual, Content, Typography) '
        f'and by responsible party (Developer / Designer / Both). '
        f'This analysis is intended to support PM planning, HR performance review, and process improvement.'
    )
    exec_data = [[Paragraph('<b>Executive Summary</b>', ParagraphStyle('eh', fontName='Helvetica-Bold', fontSize=10, leading=14, textColor=C_BLUE))],
                 [Paragraph(exec_text, ParagraphStyle('eb', fontName='Helvetica', fontSize=9, leading=13, textColor=C_DARK))]]
    exec_tbl = Table(exec_data, colWidths=[cw])
    exec_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_BLUE_LIGHT),
        ('LINEBEFORE', (0,0), (0,-1), 3, C_BLUE),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ('TOPPADDING', (0,0), (-1,-1), 9),
        ('BOTTOMPADDING', (0,0), (-1,-1), 9),
    ]))
    story.append(exec_tbl)
    story.append(PageBreak())

    # ── PAGE 2: CATEGORY BREAKDOWN ─────────────────────────────────────────────
    story.append(Paragraph('SECTION 1', S['section_label']))
    story.append(Paragraph('Issue Category Breakdown', S['h2']))
    story.append(ColorHR())
    story.append(Spacer(1, 4))

    # Prepare ordered category data
    type_order = sorted(by_type.index.tolist(),
                        key=lambda x: CATEGORY_META.get(x, {}).get('order', 99))
    bar_data    = []
    bar_colors  = []
    stacked_data= []
    for itype in type_order:
        row   = by_type.loc[itype]
        tot   = int(row['Total'])
        pct   = f"{round(tot / total * 100, 1)}%" if total else "0%"
        meta  = CATEGORY_META.get(itype, CATEGORY_META['Other'])
        bar_data.append((itype, tot, pct))
        bar_colors.append(hex_to_color(meta['color']))
        stacked_data.append((itype, {
            'Developer': int(row.get('Developer', 0)),
            'Designer':  int(row.get('Designer', 0)),
            'Both':      int(row.get('Both', 0)),
        }))

    story.append(Paragraph('Total issues by category', S['body_muted']))
    story.append(HorizBarChart(bar_data, bar_colors, height=150))
    story.append(Spacer(1, 8))
    story.append(Paragraph('Developer vs Designer split per category', S['body_muted']))
    story.append(StackedBarChart(
        stacked_data,
        [('Developer', '#0F6E56'), ('Designer', '#185FA5'), ('Both', '#854F0B')],
        height=150
    ))
    story.append(Spacer(1, 8))

    # Category detail table
    story.append(Paragraph('Detailed category summary', S['body_muted']))
    story.append(Spacer(1, 3))

    thead = ['Category', 'Total', '%', 'Developer', 'Designer', 'Both', 'Primary Owner']
    trows = [thead]
    for itype in type_order:
        row  = by_type.loc[itype]
        tot  = int(row['Total'])
        dv   = int(row.get('Developer', 0))
        ds   = int(row.get('Designer', 0))
        bt   = int(row.get('Both', 0))
        pct  = f"{round(tot / total * 100, 1)}%" if total else "0%"
        owner = 'Designer' if ds > dv else 'Developer'
        if bt >= dv and bt >= ds: owner = 'Shared'
        trows.append([itype, str(tot), pct, str(dv), str(ds), str(bt), owner])
    trows.append(['Grand Total', str(total), '100%', str(dev_cnt), str(des_cnt), str(both_cnt), ''])

    col_w = [cw*0.28, cw*0.08, cw*0.08, cw*0.11, cw*0.11, cw*0.08, cw*0.26]
    cat_tbl = Table(trows, colWidths=col_w)
    ts = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_DARK), ('TEXTCOLOR', (0,0), (-1,0), C_WHITE),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,-1), 8),
        ('LEADING', (0,0), (-1,-1), 11), ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ('ALIGN', (0,0), (0,-1), 'LEFT'), ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5), ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [C_WHITE, C_LIGHT_GRAY]),
        ('GRID', (0,0), (-1,-1), 0.4, C_BORDER),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (0,-1), (-1,-1), C_LIGHT_GRAY),
        ('LINEABOVE', (0,-1), (-1,-1), 1, C_DARK),
    ])
    for i, itype in enumerate(type_order):
        meta = CATEGORY_META.get(itype, CATEGORY_META['Other'])
        cat_tbl.setStyle(TableStyle([
            ('TEXTCOLOR', (0, i+1), (0, i+1), hex_to_color(meta['color'])),
            ('FONTNAME',  (0, i+1), (0, i+1), 'Helvetica-Bold'),
        ]))
    cat_tbl.setStyle(ts)
    story.append(cat_tbl)
    story.append(PageBreak())

    # ── PAGE 3: KEY OBSERVATIONS ───────────────────────────────────────────────
    story.append(Paragraph('SECTION 2', S['section_label']))
    story.append(Paragraph('Key Observations for PM & HR', S['h2']))
    story.append(ColorHR())
    story.append(Spacer(1, 5))

    # Auto-generate insights from data
    top_type     = type_order[0] if type_order else 'N/A'
    top_type_row = by_type.loc[top_type] if top_type in by_type.index else None
    top_page     = by_page.index[0] if not by_page.empty else 'N/A'
    top_page_cnt = int(by_page.iloc[0]['Total']) if not by_page.empty else 0

    designer_dom = des_cnt > dev_cnt
    owner_label  = 'Designer' if designer_dom else 'Developer'
    owner_pct    = des_pct if designer_dom else dev_pct

    insights = [
        (C_BLUE, C_BLUE_LIGHT,
         f'{owner_label} issues are dominant at {owner_pct}%',
         f'Out of {total} reviewed issues, {des_cnt} are Designer-owned ({des_pct}%) and {dev_cnt} are Developer-owned ({dev_pct}%). '
         f'This ratio indicates where the team should focus training and process improvements.'),
        (C_AMBER, C_AMBER_LIGHT,
         f'"{top_type}" is the most common issue category',
         f'{top_type} issues account for {top_type_row["Total"] if top_type_row is not None else 0} issues '
         f'({round(top_type_row["Total"] / total * 100, 1) if top_type_row is not None else 0}% of total). '
         f'This is the highest priority area for process improvement.'),
        (C_CORAL, C_CORAL_LIGHT,
         f'"{top_page}" has the highest issue concentration',
         f'This page carries {top_page_cnt} reviewed issues — the most of any page in the project. '
         f'Complex interactions, animations, and responsive layouts are typically the primary drivers of high issue counts.'),
        (C_TEAL, C_TEAL_LIGHT,
         'ADA / Accessibility errors require priority attention',
         'Any ADA/accessibility errors flagged should be treated as high priority. '
         'These affect legal compliance and user experience for all visitors. '
         'Developer team should run an accessibility audit before final delivery.'),
        (C_PURPLE, C_PURPLE_LIGHT,
         'Design-to-dev handoff needs tighter Figma specs',
         'The volume of spacing, padding, typography, and layout issues across pages suggests '
         'Figma annotations are not detailed enough. Recommend adding explicit pixel values, '
         'component states, and responsive breakpoints to all Figma files before development begins.'),
    ]

    for col, bg, head, body in insights:
        idata = [
            [Paragraph(head, ParagraphStyle('ih', fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=col))],
            [Paragraph(body, ParagraphStyle('ib', fontName='Helvetica', fontSize=8, leading=12, textColor=C_DARK))],
        ]
        itbl = Table(idata, colWidths=[cw])
        itbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), bg),
            ('LINEBEFORE', (0,0), (0,-1), 3, col),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ('TOPPADDING', (0,0), (-1,-1), 7),
            ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ]))
        story.append(itbl)
        story.append(Spacer(1, 5))

    # Top recurring bug patterns
    story.append(Spacer(1, 4))
    story.append(Paragraph('SECTION 3', S['section_label']))
    story.append(Paragraph('Top Recurring Issue Patterns', S['h2']))
    story.append(ColorHR())
    story.append(Spacer(1, 4))

    # Find bugs that appear across multiple pages
    bug_page = reviewed.groupby('Bug')['PageName'].nunique()
    bug_cat  = reviewed.groupby('Bug')['IssueType'].first()
    bug_owner= reviewed.groupby('Bug')['Category'].first()
    bug_count= reviewed.groupby('Bug').size()

    recurring = (
        bug_count[bug_count >= 2]
        .reset_index()
        .rename(columns={0: 'Count'})
        .assign(Pages=lambda x: x['Bug'].map(bug_page))
        .assign(IssueType=lambda x: x['Bug'].map(bug_cat))
        .assign(Owner=lambda x: x['Bug'].map(bug_owner))
        .sort_values('Count', ascending=False)
        .head(12)
    )

    if not recurring.empty:
        rhead = ['Recurring Issue', 'Category', 'Count', 'Owner', 'Across Pages']
        rrows = [rhead]
        for _, r in recurring.iterrows():
            bug_short = str(r['Bug'])[:70] + ('…' if len(str(r['Bug'])) > 70 else '')
            rrows.append([bug_short, str(r['IssueType']), str(int(r['Count'])), str(r['Owner']), str(int(r['Pages']))])

        rcol_w = [cw*0.38, cw*0.20, cw*0.08, cw*0.16, cw*0.18]
        rec_tbl = Table(rrows, colWidths=rcol_w)
        rec_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), C_DARK), ('TEXTCOLOR', (0,0), (-1,0), C_WHITE),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,-1), 7.5),
            ('LEADING', (0,0), (-1,-1), 11), ('ALIGN', (2,0), (-1,-1), 'CENTER'),
            ('ALIGN', (0,0), (1,-1), 'LEFT'), ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4), ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [C_WHITE, C_LIGHT_GRAY]),
            ('GRID', (0,0), (-1,-1), 0.4, C_BORDER),
            ('FONTNAME', (2,1), (2,-1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (2,1), (2,-1), C_BLUE),
        ]))
        story.append(rec_tbl)

    story.append(PageBreak())

    # ── PAGE 4: PAGE-LEVEL BREAKDOWN ──────────────────────────────────────────
    story.append(Paragraph('SECTION 4', S['section_label']))
    story.append(Paragraph('Page-Level Issue Breakdown', S['h2']))
    story.append(ColorHR())
    story.append(Spacer(1, 3))
    story.append(Paragraph(
        f'All {len(by_page)} pages reviewed. Sorted by total issues descending. '
        f'Filter: Status = REVIEWED only.',
        S['body_muted']
    ))
    story.append(Spacer(1, 5))

    phead = ['#', 'Page / Section', 'Total', 'Developer', 'Designer', 'Both']
    prows = [phead]
    for i, (page, row) in enumerate(by_page.iterrows()):
        prows.append([
            str(i + 1),
            str(page)[:45],
            str(int(row['Total'])),
            str(int(row.get('Developer', 0))),
            str(int(row.get('Designer', 0))),
            str(int(row.get('Both', 0))),
        ])
    prows.append(['', 'Grand Total', str(total), str(dev_cnt), str(des_cnt), str(both_cnt)])

    pcol_w = [cw*0.05, cw*0.40, cw*0.10, cw*0.14, cw*0.14, cw*0.10]
    page_tbl = Table(prows, colWidths=pcol_w, repeatRows=1)
    pts = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_DARK), ('TEXTCOLOR', (0,0), (-1,0), C_WHITE),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,-1), 8),
        ('LEADING', (0,0), (-1,-1), 11), ('ALIGN', (2,0), (-1,-1), 'CENTER'),
        ('ALIGN', (0,0), (1,-1), 'LEFT'), ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4), ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [C_WHITE, C_LIGHT_GRAY]),
        ('GRID', (0,0), (-1,-1), 0.4, C_BORDER),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (0,-1), (-1,-1), C_LIGHT_GRAY),
        ('LINEABOVE', (0,-1), (-1,-1), 1, C_DARK),
    ])
    # Highlight top 3 pages
    highlight = [colors.HexColor('#EBF4FF'), colors.HexColor('#F0FBF7'), colors.HexColor('#FEF8F5')]
    for idx, hc in enumerate(highlight):
        if idx + 1 < len(prows):
            page_tbl.setStyle(TableStyle([('BACKGROUND', (0, idx+1), (-1, idx+1), hc)]))
    page_tbl.setStyle(pts)
    story.append(page_tbl)
    story.append(Spacer(1, 10))

    # Notes footer
    note = (
        '<b>Notes:</b>  Issues with status DISCUSSED / NEED TO DISCUSS / "Need to share with client" are excluded.  |  '
        f'Data loaded directly from Google Sheets: {project_name}.  |  '
        f'Report auto-generated by QA Report Tool — Encircle Technologies.  |  '
        f'Generated on: {today}.'
    )
    note_tbl = Table([[Paragraph(note, ParagraphStyle('nb', fontName='Helvetica', fontSize=7.5, leading=11, textColor=C_MUTED))]], colWidths=[cw])
    note_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_LIGHT_GRAY),
        ('LINEABOVE', (0,0), (-1,0), 1.5, C_BLUE),
        ('LEFTPADDING', (0,0), (-1,-1), 10), ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 8), ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(note_tbl)

    # Build
    page_fn = _on_page(project_name, today)
    doc.build(story, onFirstPage=page_fn, onLaterPages=page_fn)
