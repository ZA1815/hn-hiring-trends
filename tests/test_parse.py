import pytest

from pipeline.parse import classify, html_to_text, salary_ranges


def test_html_to_text_unescapes_and_keeps_paragraphs():
    raw = 'Acme | Engineer<p>Apply at <a href="x">https:&#x2F;&#x2F;acme.com</a> &amp; say hi'
    assert html_to_text(raw) == "Acme | Engineer\nApply at https://acme.com & say hi"


@pytest.mark.parametrize(
    "text, expected",
    [
        ("$120k - $180k", [(120_000, 180_000)]),
        ("$120K–180K + equity", [(120_000, 180_000)]),
        ("$120,000 to $165,000", [(120_000, 165_000)]),
        ("$140-190k base", [(140_000, 190_000)]),
        ("150k - 200k USD", [(150_000, 200_000)]),
        ("$95.5k-$110k", [(95_500, 110_000)]),
        ("Senior: $160k-$200k, Staff: $200k-$250k", [(160_000, 200_000), (200_000, 250_000)]),
        ("AWS, Terraform) - $135-$155k -https://x", [(135_000, 155_000)]),
        ("COMPENSATION: $180,000--$250,000 depending", [(180_000, 250_000)]),
        ("| $181K base + 15% bonus", [(181_000, 181_000)]),
        ("Browser Platform - $178,500 USD + equity", [(178_500, 178_500)]),
    ],
)
def test_salary_ranges_formats(text, expected):
    assert salary_ranges(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "$60-90k/hr",               # hourly
        "$60k-$90k per hour",       # hourly
        "raised $15-20M",           # funding, not pay
        "$10k-$50k",                # implausible annual spread / too low
        "Series B, 50-200 employees",
        "$3,500-$5,000 USD/month",   # monthly
        "We raised $150k in pre-seed",
        "plus a $50k signing bonus",
        "manages $100,000,000 daily",
    ],
)
def test_salary_ranges_rejects_non_salary(text):
    assert salary_ranges(text) == []


def test_arrangement():
    assert classify("Acme | REMOTE (US)").arrangement == "remote"
    assert classify("Acme | ONSITE, no remote").arrangement == "onsite"
    assert classify("Acme | Hybrid in NYC").arrangement == "hybrid"
    assert classify("Acme | Remote or onsite in SF").arrangement == "hybrid"
    assert classify("Acme | Engineer").arrangement == "unspecified"


@pytest.mark.parametrize(
    "text, present, absent",
    [
        ("Stack: Go, Postgres, React", {"Go", "PostgreSQL", "React"}, {"React Native"}),
        ("We use React Native and TypeScript", {"React Native", "TypeScript"}, {"React"}),
        ("A go-to partner. Go to our site.", set(), {"Go"}),
        ("JavaScript and Java", {"JavaScript", "Java"}, set()),
        ("C#, ASP.NET, visit example.net", {"C# / .NET"}, set()),
        ("We react quickly to feedback", set(), {"React"}),
        ("LLM agents with RAG", {"LLMs / GenAI"}, set()),
        ("node graph in Python", {"Python"}, {"Node.js"}),
    ],
)
def test_tech_detection(text, present, absent):
    techs = classify(text).techs
    assert present <= techs
    assert not (absent & techs)


def test_visa_negation():
    assert classify("Visa sponsorship available").visa_offered
    assert not classify("We cannot offer visa sponsorship").visa_offered
    assert not classify("No visa sponsorship").visa_offered


def test_salary_midpoint_uses_median_of_ranges():
    post = classify("Senior: $160k-$200k, Staff: $200k-$240k, Principal: $240k-$300k")
    assert post.salary_mid == 220_000
