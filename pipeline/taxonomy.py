"""Patterns that classify a job post.

Each technology maps to one compiled regex. Ambiguous words ("Go", "React",
"Node", "Swift", "AI") are matched case-sensitively; everything else is
case-insensitive via scoped ``(?i:...)`` groups.
"""

import re

_TECH_PATTERNS: dict[str, str] = {
    # Languages
    "Python": r"(?i:\bpython\b)",
    "JavaScript": r"(?i:\bjavascript\b)|\bJS\b",
    "TypeScript": r"(?i:\btypescript\b)",
    "Java": r"(?i:\bjava\b)(?!\s*[Ss]cript)",
    "Go": r"(?i:\bgolang\b)|\bGo\b(?!-to\b|\s+(?:to|live|ahead|after|beyond|for|with)\b)",
    "Rust": r"(?i:\brust\b)",
    "Ruby / Rails": r"(?i:\bruby\b|\brails\b)",
    "PHP": r"(?i:\bphp\b|\blaravel\b)",
    "C# / .NET": r"(?i:\bc#|(?<![\w/])\.net\b|\bdotnet\b|\basp\.net\b)",
    "C++": r"(?i:\bc\+\+)",
    "Kotlin": r"(?i:\bkotlin\b)",
    "Swift": r"\bSwift(?:UI)?\b",
    "Scala": r"(?i:\bscala\b)",
    "Elixir": r"(?i:\belixir\b)",
    # Front end
    "React": r"\bReact(?:\.?[jJ][sS])?\b(?!\s+Native)",
    "Vue": r"(?i:\bvue(?:\.?js)?\b)",
    "Angular": r"(?i:\bangular(?:js)?\b)",
    "Svelte": r"(?i:\bsvelte(?:kit)?\b)",
    "Next.js": r"(?i:\bnext\.?js\b)",
    # Back end
    "Node.js": r"(?i:\bnode\.?js\b)|\bNode\b",
    "Django": r"(?i:\bdjango\b)",
    # Mobile
    "iOS": r"(?i:\bios\b)",
    "Android": r"(?i:\bandroid\b)",
    "React Native": r"(?i:\breact[\s-]native\b)",
    "Flutter": r"(?i:\bflutter\b)",
    # Data stores
    "PostgreSQL": r"(?i:\bpostgres(?:ql)?\b)",
    "MySQL": r"(?i:\bmysql\b)",
    "MongoDB": r"(?i:\bmongo(?:db)?\b)",
    "Redis": r"(?i:\bredis\b)",
    "Kafka": r"(?i:\bkafka\b)",
    "Spark": r"\bSpark\b|(?i:\bpyspark\b)",
    "Snowflake": r"\bSnowflake\b",
    # Cloud and infrastructure
    "AWS": r"(?i:\baws\b|\bamazon web services\b)",
    "GCP": r"(?i:\bgcp\b|\bgoogle cloud\b)",
    "Azure": r"(?i:\bazure\b)",
    "Kubernetes": r"(?i:\bkubernetes\b|\bk8s\b)",
    "Docker": r"(?i:\bdocker\b)",
    "Terraform": r"(?i:\bterraform\b|\bopentofu\b)",
    # AI and data
    "LLMs / GenAI": (
        r"(?i:\bllms?\b|\bgen\s?ai\b|\bgenerative ai\b|\bchatgpt\b|\bgpt-?\d"
        r"|\blarge language models?\b|\bai agents?\b|\bagentic\b)|\bRAG\b"
    ),
    "Machine learning": r"(?i:\bmachine learning\b|\bdeep learning\b)|\bML\b",
    "Crypto / Web3": r"(?i:\bblockchain\b|\bcryptocurrenc(?:y|ies)\b|\bweb3\b|\bsolidity\b|\bethereum\b|\bdefi\b)",
}

TECH: dict[str, re.Pattern[str]] = {name: re.compile(p) for name, p in _TECH_PATTERNS.items()}

REMOTE = re.compile(r"(?i:(?<!\bno )(?<!\bnot )(?<!\bnon-)(?<!\bnon )\bremote\b)")
HYBRID = re.compile(r"(?i:\bhybrid\b)")
ONSITE = re.compile(r"(?i:\bon[\s-]?site\b|\bin[\s-]office\b|\bin[\s-]person\b)")

VISA = re.compile(r"(?i:\bvisas?\b|\bsponsorship\b|\bsponsor\b|\bh-?1b\b)")
VISA_NEGATED = re.compile(
    r"(?i:\b(?:no|not|unable to|cannot|can't|can not|don't|do not|won't|will not|without)\b"
    r"[^.|\n]{0,40}\b(?:visas?|sponsor(?:ship)?|h-?1b)\b)"
)

JUNIOR = re.compile(r"(?i:\bjunior\b|\bjr\.?(?=\s)|\bentry[\s-]level\b|\bnew[\s-]grads?\b|\bgraduates?\b)")
INTERN = re.compile(r"(?i:\binterns?(?:hips?)?\b)")
