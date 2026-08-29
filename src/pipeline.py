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
        return round(self.viral_potential * 0.30 + self.hook_strength * 0.20 + self.curiosity * 0.15 + self.visual_potential * 0.15 + self.monetization * 0.10 + self.freshness * 0.10)


@dataclass
class Scene:
    start_sec: float
    end_sec: float
    narration: str
    visual_direction: str
    caption: str
    visual_type: str = "cinematic-image"
    composition: str = "full-frame-9:16"
    camera_motion: str = "slow-dolly-in"
    transition: str = "cinematic-cut"
    caption_zone: str = "lower-safe-zone"
    motion_intensity: float = 0.35
    sfx_cue: str = "subtle-whoosh"
    presenter_allowed: bool = False


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
    fps: int = 30
    style_profile: str = "khalf-al-raqam-v4"
    visual_qc_threshold: float = 8.3


class ContentPipeline:
    """V4 cinematic DataStory production director."""

    def score_idea(self, idea: str) -> ScoreBreakdown:
        text = idea.lower()
        money_terms = ("مليار", "مليون", "مال", "ربح", "خس", "شركة")
        tech_terms = ("تقني", "ذكاء", "ai", "تطبيق", "google", "شركة")
        money_hits = sum(term in text for term in money_terms)
        tech_hits = sum(term in text for term in tech_terms)
        return ScoreBreakdown(min(95, 68 + money_hits * 4 + tech_hits * 2), min(95, 70 + money_hits * 4), min(95, 72 + (8 if "رفض" in text else 0)), min(92, 68 + tech_hits * 4), min(92, 70 + money_hits * 3), 65)

    def build_hook_candidates(self, idea: str) -> List[str]:
        return [
            "قرار واحد قد يحوّل فرصة صغيرة إلى خسارة بمليارات.",
            "رقم واحد بدا عاديًا وقتها… ثم غيّر القصة كلها.",
            "كيف يمكن لقرار منطقي أن يتحول إلى واحد من أغلى الأخطاء؟",
        ]

    def build_hook(self, idea: str) -> str:
        return self.build_hook_candidates(idea)[0]

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
            Scene(0, 3, hook, "Extreme macro decision document, dramatic light, giant kinetic number reveal, deep blacks, cyan-gold accents", "قرار بمليارات؟", "number-reveal", camera_motion="fast-push-in", transition="impact-cut", motion_intensity=0.70, sfx_cue="bass-impact"),
            Scene(3, 12, "تنتشر على الإنترنت قصص عن فرص ضائعة صنعت شركات عملاقة.", "Native vertical cinematic old office and contract montage with valuation graph integrated into the environment; no floating cards", "قصة منتشرة جدًا", "cinematic-montage", camera_motion="parallax-dolly", transition="motion-blur-cut", motion_intensity=0.48),
            Scene(12, 24, "لكن Content Factory لا يحول القصة مباشرة إلى فيديو.", "Dark documentary source verification desk, evidence timeline and source markers physically integrated into scene", "أولًا: تحقق", "data-story", camera_motion="slow-orbit", transition="match-cut", sfx_cue="paper-hit"),
            Scene(24, 38, "نراجع المصدر والتاريخ والأرقام والسياق قبل كتابة النسخة النهائية.", "Animated vertical timeline with large mobile-readable dates and numbers, dark premium documentary styling", "المصدر • التاريخ • الأرقام", "timeline", camera_motion="vertical-track", transition="timeline-swipe", motion_intensity=0.42),
            Scene(38, 50, "إذا ثبتت، نحكيها. وإذا لم تثبت، نستبدلها بقصة موثقة أقوى.", "Cinematic before-after comparison filling the entire vertical frame; approved evidence wins with gold number payoff", "القصة الأقوى هي القصة الصحيحة", "comparison", camera_motion="slow-pull-back", transition="cinematic-fade", sfx_cue="payoff-rise"),
        ]

    def run(self, idea: str) -> ProductionPackage:
        score = self.score_idea(idea)
        hook = self.build_hook(idea)
        script = self.build_script(idea)
        return ProductionPackage(idea=idea, score=score, approved=score.total >= 70, hook=hook, script=script, scenes=self.storyboard(hook, script))
