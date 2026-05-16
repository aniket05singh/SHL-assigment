"""Generate public eval traces from catalog keyword search (proxy labels)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.catalog import Catalog
from app.retrieval import Retriever

OUT = Path(__file__).resolve().parents[1] / "eval" / "traces" / "public"

PERSONAS = [
    {
        "id": "java_mid_stakeholder",
        "turns": [
            {"user": "I am hiring a Java developer who works with stakeholders"},
            {"user": "Mid-level, around 4 years"},
        ],
        "query": "java developer mid-level stakeholder communication",
    },
    {
        "id": "python_data_senior",
        "turns": [
            {"user": "Senior Python data engineer, 8 years experience"},
            {"user": "Need technical skills and cognitive ability, under 45 minutes"},
        ],
        "query": "python data engineer senior cognitive technical skills",
    },
    {
        "id": "contact_center",
        "turns": [
            {"user": "Hiring contact center customer service agents"},
            {"user": "Entry level, multitasking and communication important"},
        ],
        "query": "contact center customer service entry communication multitasking",
    },
    {
        "id": "sales_manager",
        "turns": [
            {"user": "Regional sales manager role"},
            {"user": "Need leadership personality and sales skills assessments"},
        ],
        "query": "sales manager leadership personality sales",
    },
    {
        "id": "net_fullstack",
        "turns": [
            {"user": "Hiring .NET full stack developer"},
            {"user": "Mid-professional, MVC and SQL skills"},
        ],
        "query": ".net mvc sql developer mid-professional",
    },
    {
        "id": "graduate_general",
        "turns": [
            {"user": "Graduate hire general population cognitive"},
            {"user": "Ability and aptitude, english"},
        ],
        "query": "graduate general population cognitive aptitude verify",
    },
    {
        "id": "nurse_healthcare",
        "turns": [
            {"user": "Hiring registered nurse for hospital"},
            {"user": "Clinical knowledge and patient care"},
        ],
        "query": "nursing healthcare clinical patient",
    },
    {
        "id": "sap_consultant",
        "turns": [
            {"user": "SAP SD consultant hiring"},
            {"user": "Professional individual contributor, configuration skills"},
        ],
        "query": "sap sd sales distribution consultant",
    },
    {
        "id": "personality_only",
        "turns": [
            {"user": "I want personality and behavior assessment OPQ"},
            {"user": "For manager role, no technical tests"},
        ],
        "query": "personality behavior opq manager",
    },
    {
        "id": "jd_paste",
        "turns": [
            {
                "user": "Here is text from job description: Java Spring Boot microservices, REST APIs, 5 years, collaborates with product owners"
            },
        ],
        "query": "java spring boot microservices rest api product",
    },
]


def main() -> None:
    cat = Catalog.load()
    retriever = Retriever(cat)
    OUT.mkdir(parents=True, exist_ok=True)
    for p in PERSONAS:
        results = retriever.search(p["query"], top_k=15)
        relevant = [r.assessment.to_recommendation() for r in results[:12]]
        trace = {
            "id": p["id"],
            "turns": p["turns"],
            "relevant": relevant,
        }
        (OUT / f"{p['id']}.json").write_text(
            json.dumps(trace, indent=2), encoding="utf-8"
        )
        print(p["id"], len(relevant), "labels")


if __name__ == "__main__":
    main()
