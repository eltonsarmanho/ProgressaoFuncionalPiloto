"""SEG-11 (W03): MAX_MEGAPIXELS reaches the decode guard of the file inspector."""

import io

import pytest
from PIL import Image


@pytest.fixture
def truncated_png(tmp_path):
    """A 1.44 megapixel PNG whose data is cut in half: valid header, unreadable body."""
    noise = Image.effect_noise((1200, 1200), 80)
    buffer = io.BytesIO()
    noise.save(buffer, format="PNG")
    data = buffer.getvalue()
    path = tmp_path / "cortada.png"
    path.write_bytes(data[: len(data) // 2])
    return path


def test_an_image_above_the_setting_is_measured_but_not_decoded(make_client, truncated_png):
    client = make_client(max_megapixels=1)
    facts = client.app.state.container.inspector.inspect(truncated_png)
    assert facts.megapixels is not None and facts.megapixels > 1
    assert facts.is_readable is True  # above the limit: the body is never read


def test_the_same_image_under_the_default_limit_is_decoded_and_found_unreadable(
    make_client, truncated_png
):
    client = make_client()
    facts = client.app.state.container.inspector.inspect(truncated_png)
    assert facts.is_readable is False
