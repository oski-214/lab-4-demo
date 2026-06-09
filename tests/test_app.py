from app.backend.app import activities, app, get_activities, get_open_spots, render_activities_page


def test_get_activities_still_returns_json():
    assert get_activities() == activities


def test_activities_view_route_is_registered():
    assert any(route.path == "/activities/view" for route in app.routes)


def test_get_open_spots_handles_partial_full_and_overfull_activities():
    assert get_open_spots({"max_participants": 10, "participants": ["a", "b"]}) == 8
    assert get_open_spots({"max_participants": 2, "participants": ["a", "b"]}) == 0
    assert get_open_spots({"max_participants": 1, "participants": ["a", "b"]}) == 0


def test_activities_view_lists_schedule_and_open_spots():
    page = render_activities_page()

    assert '<link rel="stylesheet" href="/static/styles.css"' in page
    assert 'class="activities-overview"' in page

    for name, activity in activities.items():
        assert name in page
        assert activity["schedule"] in page
        assert f"Spots open:</strong> {get_open_spots(activity)}" in page
