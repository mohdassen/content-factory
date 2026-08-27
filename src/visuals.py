from dataclasses import dataclass
from typing import List

@dataclass
class VisualShot:
    start: float
    end: float
    prompt: str
    motion: str = 'slow_zoom'


def netflix_blockbuster_visual_plan() -> List[VisualShot]:
    return [
        VisualShot(0, 5, 'cinematic 2000s video rental store exterior at night, nostalgic, dramatic, vertical 9:16'),
        VisualShot(5, 11, 'small early internet startup office in 2000, founders reviewing numbers, cinematic documentary, vertical 9:16'),
        VisualShot(11, 18, 'business meeting table, two companies negotiating acquisition, tense corporate atmosphere, no logos, vertical 9:16'),
        VisualShot(18, 23, 'bold symbolic rejection moment, contract pushed away across table, cinematic close-up, vertical 9:16'),
        VisualShot(23, 33, 'dot-com crash visual metaphor, falling market screens and empty startup office, documentary realism, vertical 9:16'),
        VisualShot(33, 43, 'transition from mailed DVD envelope to modern streaming screen, elegant technology evolution, vertical 9:16'),
        VisualShot(43, 49, 'empty abandoned video rental store shelves, cinematic melancholy, vertical 9:16'),
        VisualShot(49, 55, 'futuristic market change metaphor, road splitting into old world and digital future, cinematic, vertical 9:16'),
    ]
