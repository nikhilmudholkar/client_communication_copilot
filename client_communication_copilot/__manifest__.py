{
    'name': 'ChatGPT to automate order updates from customer emails(beta)',
    'version': '1.0',
    'category': 'Extra Tools',
    'sequence': '-100',
    'description': """Bryo reads and understands customer emails, extracts relevant information about the order, assists users on how to update Odoo and notifies the relevant stakeholders.""",
    'author': 'Bryo UG',
    'maintainer': 'Bryo UG',
    'license': 'LGPL-3',
    'website': 'https://www.bryo.io',
    'summary': 'Bryo reads and understands customer emails, extracts relevant information about the order, assists users on how to update Odoo and notifies the relevant stakeholders.',
    "keywords": ["email", "purchase order", "vendor", "email parser", "parser", "bard", "chatgpt", "openai", "AI", "copilot", "llm"],
    'data': [
        'data/client_copilot_channel_data.xml',
        'data/copilot_user_partner_data.xml',
    ],
    "depends": [
        "sale",
        "sale_stock",
        "mrp",
        "purchase"
    ],
    "external_dependencies": {
       'python': ["pandas"],
    },
    'images': ['static/description/banner.png', 'static/description/icon.png'],
    'installable': True,
}