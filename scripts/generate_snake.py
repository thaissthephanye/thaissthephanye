"""Generate light and dark contribution-grid animations using GitHub's GraphQL API."""

import json
import os
from pathlib import Path
from urllib.request import Request, urlopen


USERNAME = "thaissthephanye"
QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks {
          contributionDays { date weekday contributionCount contributionLevel }
        }
      }
    }
  }
}
"""
LEVELS = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}
PALETTES = {
    "github-contribution-grid-snake.svg": (
        "#c33175",
        ("#f7eef3", "#f1c5da", "#e789b3", "#d75b98", "#b53678"),
    ),
    "github-contribution-grid-snake-dark.svg": (
        "#ff5ca8",
        ("#222b36", "#582d4e", "#8b3f74", "#c35b9e", "#f38ac0"),
    ),
}


def fetch_calendar():
    token = os.environ["GITHUB_TOKEN"]
    payload = json.dumps({"query": QUERY, "variables": {"login": USERNAME}}).encode()
    request = Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "thaissthephanye-profile-readme",
        },
    )
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError(result["errors"])
    user = result.get("data", {}).get("user")
    if not user:
        raise RuntimeError("GitHub user not found")
    return user["contributionsCollection"]["contributionCalendar"]


def render(calendar, snake_color, colors):
    weeks = calendar["weeks"]
    if not weeks:
        raise ValueError("The contribution calendar is empty")

    step, offset = 15, 16
    width, height = len(weeks) * step + 2 * offset, 7 * step + 2 * offset
    cells = []
    for column, week in enumerate(weeks):
        for day in week["contributionDays"]:
            row = day["weekday"]
            level = LEVELS[day["contributionLevel"]]
            x, y = offset + column * step, offset + row * step
            cells.append(
                f'<rect x="{x - 5}" y="{y - 5}" width="11" height="11" '
                f'rx="2" fill="{colors[level]}"/>'
            )

    # The path visits every square in the familiar GitHub calendar order.
    points = []
    for row in range(7):
        columns = range(len(weeks)) if row % 2 == 0 else range(len(weeks) - 1, -1, -1)
        points.extend((offset + column * step, offset + row * step) for column in columns)
    path = "M " + " L ".join(f"{x} {y}" for x, y in points)
    length = (len(points) - 1) * step

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img" '
        'aria-label="Cobrinha rosa percorrendo as contribuições de Thais Sthephanye">'
        '<title>Contribuições de Thais Sthephanye</title>'
        '<style>'
        f'@keyframes travel{{to{{stroke-dashoffset:-{length};}}}}'
        f'.snake{{stroke-dasharray:70 {length};animation:travel 28s linear infinite;}}'
        '@media (prefers-reduced-motion:reduce){.snake{animation:none;}}'
        '</style>'
        + "".join(cells)
        + f'<path class="snake" d="{path}" fill="none" stroke="{snake_color}" '
        'stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>'
        '</svg>\n'
    )


def main():
    calendar = fetch_calendar()
    output = Path("dist")
    output.mkdir(exist_ok=True)
    for filename, (snake_color, colors) in PALETTES.items():
        (output / filename).write_text(
            render(calendar, snake_color, colors), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
