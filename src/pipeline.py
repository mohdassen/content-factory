from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class ScoreBreakdown:
    viral_potential: int
    hook_strength: int
    curiosity: int
    visual_potential: int
    monetization: int
    freshness: int

    @property
    def total(self) -> int:
        return round(
            self.viral_potential * 0.30
            + self.hook_strength * 0.20
            + self.curiosity * 0.15
            + self.visual_potential * 0.15
            + self.monetization * 0.10
            + self.freshness * 0.10
        )


@dataclass
class Scene:
    start_sec: float
    end_sec: float
    narration: str
    visual_direction: str
    caption: str


@dataclass
class ProductionPackage:
    idea: str
    score: ScoreBreakdown
    approved: bool
    hook: str
    script: str
    scenes: List[Scene] = field(default_factory=list)
    fact_check_status: str = "research-required"
    target_duration_sec: int = 50
    aspect_ratio: str = "9:16"
    output_resolution: str = "1080x1920"


class ContentPipeline:
    """Deterministic V1 pipeline.

    This layer creates a safe production package without pretending that an
    unverified story is factual. External research/LLM/rendering adapters can
    replace each deterministic stage later.
    """

    def score_idea(self, idea: str) -> ScoreBreakdown:
        # Conservative heuristic baseline. External trend signals will replace this.
        text = idea.lower()
        money_terms = ("مليار", "مليون", "مال", "ربح", "خس", "شركة")
        tech_terms = ("تقني", "ذكاء", "ai", "تطبيق", "google", "شركة")
        money_hits = sum(term in text for term in money_terms)
        tech_hits = sum(term in text for term in tech_terms)

        return ScoreBreakdown(
            viral_potential=min(95, 68 + money_hits * 4 + tech_hits * 2),
            hook_strength=min(95, 70 + money_hits * 4),
            curiosity=min(95, 72 + (8 if "رفض" in text else 0)),
            visual_potential=min(92, 68 + tech_hits * 4),
            monetization=min(92, 70 + money_hits * 3),
            freshness=65,
        )

    def build_hook(self, idea: str) -> str:
        return "قرار واحد قد يحوّل فرصة صغيرة إلى خسارة بمليارات… لكن هل القصة فعلًا صحيحة؟"

    def build_script(self, idea: str) -> str:
        return (
            "تنتشر على الإنترنت قصص عن شركات رفضت فرصًا بدت صغيرة ثم أصبحت قيمتها مليارات. "
            "لكن قبل أن نحول أي قصة إلى فيديو، نتحقق من المصدر والتاريخ والأرقام. "
            "إذا ثبتت القصة، نروي القرار، لماذا بدا منطقيًا وقتها، وما الذي حدث بعده. "
            "وإذا لم تثبت، نستبدلها بقصة موثقة أقوى بدل نشر معلومة جذابة لكنها خاطئة. "
            "الهدف ليس الصدمة فقط؛ الهدف قصة سريعة تستطيع الوثوق بها."
        )

    def storyboard(self, hook: str, script: str) -> List[Scene]:
        return [
            Scene(0, 3, hook, "Extreme close-up on a decision document; kinetic number reveal", "قرار بمليارات؟"),
            Scene(3, 12, "تنتشر على الإنترنت قصص عن فرص ضائعة صنعت شركات عملاقة.", "Fast montage: old office, contract, rising valuation graph", "قصة منتشرة جدًا"),
            Scene(12, 24, "لكن Content Factory لا يحول القصة مباشرة إلى فيديو.", "Source cards slide in; verification stamps; timeline", "أولًا: تحقق"),
            Scene(24, 38, "نراجع المصدر والتاريخ والأرقام والسياق قبل كتابة النسخة النهائية.", "Animated checklist with primary-source emphasis", "المصدر • التاريخ • الأرقام"),
            Scene(38, 50, "إذا ثبتت، نحكيها. وإذا لم تثبت، نستبدلها بقصة موثقة أقوى.", "Split screen: rejected rumor vs approved sourced story", "القصة الأقوى هي القصة الصحيحة"),
        ]

    def run(self, idea: str) -> ProductionPackage:
        score = self.score_idea(idea)
        hook = self.build_hook(idea)
        script = self.build_script(idea)
        return ProductionPackage(
            idea=idea,
            score=score,
            approved=score.total >= 70,
            hook=hook,
            script=script,
            scenes=self.storyboard(hook, script),
        )
