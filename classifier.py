"""
classifier.py
─────────────
Classifies each bug description into one of 6 issue categories.
Edit the keyword lists below to tune classification for your projects.
"""


# ── CATEGORY DEFINITIONS ────────────────────────────────────────────────────────
# Each category has a priority (checked top to bottom) and a keyword list.
# The FIRST matching category wins.

CATEGORIES = [

    # ── 1. TYPOGRAPHY ──────────────────────────────────────────────────────────
    {
        'name': 'Typography',
        'keywords': [
            'font family', 'font-family', 'font size', 'font-size',
            'font weight', 'font-weight', 'font color', 'font-color',
            'font style', 'font-style', 'font name',
            'uppercase', 'lowercase', 'capitalized', 'capital letter',
            'small case', 'upper case', 'lower case', 'all caps',
            'text color', 'sub text font', 'typography', 'typeface',
            'line-height', 'letter spacing', 'koho', 'garamond',
            '1st letter', 'first letter', 'set d in', 'b and w need',
        ],
    },

    # ── 2. CONTENT ISSUES ──────────────────────────────────────────────────────
    {
        'name': 'Content Issues',
        'keywords': [
            'title', 'description', 'missing', 'favicon', 'caption',
            'h1', 'h2 tag', 'meta tag', 'read more', 'also update',
            'thank you text', 'update title', 'update the all card',
            'update the center image', 'update button', 'update text',
            'text to stay', 'showing double h1', 'sub title is missing',
            'stay type', 'remove the more text', 'content is missing',
            'copy is missing', 'placeholder', 'dummy text',
        ],
    },

    # ── 3. FUNCTIONAL ISSUES ───────────────────────────────────────────────────
    {
        'name': 'Functional Issues',
        'keywords': [
            'link', 'ada error', 'adaerror', 'ada issue', 'accessibility',
            'redirect', 'slider', 'click', 'popup', 'active dot',
            'dropdown', 'download pdf', 'social media', 'loop true',
            'scroll', 'sticky', 'not work', 'not working', 'not open',
            'not close', 'not load', 'not showing when', 'not able',
            'form is not open', 'enquire form', 'select other circle',
            'move down', 'menu logo', 'cursor', 'button link',
            'footer logo link', 'anchor', 'goto', 'map', 'navigation',
            'auto change', 'parallax', 'transition', 'animation',
            'hover effect', 'hover style', 'hover color',
            'not visible', 'does not work', 'broken', 'not function',
            'filter', 'search', 'sort',
        ],
    },

    # ── 4. IMAGE / VISUAL ISSUES ───────────────────────────────────────────────
    {
        'name': 'Image / Visual',
        'keywords': [
            'image', 'blur', 'gradient', 'shadow', 'overlay',
            'bg color', 'background color', 'background image',
            'hero image', 'photo', 'video', 'gallery', 'icon',
            'logo', 'banner', 'thumbnail', 'aspect ratio',
            'image size', 'image quality', 'image not same',
            'wrong image', 'black border', 'image border',
        ],
    },

    # ── 5. UI/UX & LAYOUT ──────────────────────────────────────────────────────
    {
        'name': 'UI/UX & Layout',
        'keywords': [
            'padding', 'margin', 'gap', 'spacing', 'align',
            'width', 'height', 'position', 'border', 'center',
            'side by side', 'two line', 'one line', 'responsive',
            'ipad', 'iphone', 'mobile', 'laptop', 'desktop',
            'viewport', 'layout', 'section', 'size of', 'button size',
            'card', 'row', 'grid', 'badge', 'tag', 'style',
            'color', 'colour', 'set 4', 'set 50', 'reduce the gap',
            'reduce gap', 'extra padding', 'extra space', 'extra line',
            'double line', 'showing twice', 'showing double',
            '2x2', 'columns', 'breakpoint', 'media query',
        ],
    },

    # ── 6. OTHER ───────────────────────────────────────────────────────────────
    {
        'name': 'Other',
        'keywords': [],
    },
]


# ── MAIN CLASSIFIER ─────────────────────────────────────────────────────────────
def classify_issue(bug_text: str, category: str = '') -> str:
    b = bug_text.lower().strip()
    for cat in CATEGORIES:
        if not cat['keywords']:
            return cat['name']
        for kw in cat['keywords']:
            if kw in b:
                return cat['name']
    return 'Other'


# ── CATEGORY METADATA (colors used by PDF builder) ──────────────────────────────
CATEGORY_META = {
    'UI/UX & Layout':    {'color': '#185FA5', 'light': '#E6F1FB', 'dark_text': '#0C447C', 'order': 1},
    'Functional Issues': {'color': '#854F0B', 'light': '#FAEEDA', 'dark_text': '#633806', 'order': 2},
    'Image / Visual':    {'color': '#993C1D', 'light': '#FAECE7', 'dark_text': '#712B13', 'order': 3},
    'Content Issues':    {'color': '#0F6E56', 'light': '#E1F5EE', 'dark_text': '#085041', 'order': 4},
    'Typography':        {'color': '#534AB7', 'light': '#EEEDFE', 'dark_text': '#3C3489', 'order': 5},
    'Other':             {'color': '#888780', 'light': '#F1EFE8', 'dark_text': '#444441', 'order': 6},
}


def get_all_category_names():
    return [c['name'] for c in CATEGORIES]
