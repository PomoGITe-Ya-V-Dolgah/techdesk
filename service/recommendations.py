import re
from dataclasses import dataclass

from .models import Solution, Ticket


TOKEN_RE = re.compile(r"[а-яА-Яa-zA-Z0-9]{3,}")


@dataclass
class Recommendation:
    solution: Solution
    score: int
    reason: str


def tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text or "")}


def recommend_solutions(ticket: Ticket, limit: int = 3) -> list[Recommendation]:
    """Return explainable recommendations based on equipment, category and shared words."""
    query_tokens = tokenize(f"{ticket.title} {ticket.description}")
    candidates = Solution.objects.select_related("ticket", "equipment", "created_by").exclude(ticket=ticket)
    recommendations: list[Recommendation] = []

    for solution in candidates:
        score = 0
        reasons = []
        source_ticket = solution.ticket
        if ticket.equipment_id and solution.equipment_id == ticket.equipment_id:
            score += 60
            reasons.append("то же оборудование")
        if source_ticket.category_id == ticket.category_id:
            score += 25
            reasons.append("та же категория")

        candidate_tokens = tokenize(
            f"{source_ticket.title} {source_ticket.description} {solution.problem_summary} {solution.resolution_steps}"
        )
        overlap = query_tokens & candidate_tokens
        if overlap:
            score += min(len(overlap) * 5, 30)
            reasons.append("общие ключевые слова: " + ", ".join(sorted(overlap)[:5]))

        if score > 0:
            recommendations.append(Recommendation(solution=solution, score=score, reason="; ".join(reasons)))

    recommendations.sort(key=lambda item: item.score, reverse=True)
    return recommendations[:limit]
