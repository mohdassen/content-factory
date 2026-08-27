from src.pipeline import ContentPipeline


def test_demo_pipeline_builds_valid_package():
    package = ContentPipeline().run("شركة تقنية رفضت فرصة بمليون ثم خسرت مليارات")
    assert package.score.total >= 70
    assert package.approved is True
    assert package.aspect_ratio == "9:16"
    assert package.output_resolution == "1080x1920"
    assert len(package.scenes) >= 4
    assert package.fact_check_status == "research-required"


def test_scene_timeline_is_monotonic():
    package = ContentPipeline().run("قصة شركة تقنية وخسارة بمليارات")
    starts = [scene.start_sec for scene in package.scenes]
    ends = [scene.end_sec for scene in package.scenes]
    assert starts == sorted(starts)
    assert all(end > start for start, end in zip(starts, ends))
