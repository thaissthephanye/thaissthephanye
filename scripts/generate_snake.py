"""Generate light and dark contribution-grid animations using GitHub's GraphQL API."""

import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from collections import defaultdict
from html import escape


USERNAME = "thaissthephanye"
QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(first: 100, privacy: PUBLIC, isFork: false) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
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


def fetch_profile():
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
    return user


def render_snake(calendar, snake_color, colors):
    weeks = calendar["weeks"]
    if not weeks:
        raise ValueError("The contribution calendar is empty")

    step, offset = 15, 16
    width, height = len(weeks) * step + 2 * offset, 7 * step + 2 * offset
    cells = []
    eaten_styles = []
    path_steps = len(weeks) * 7 - 1
    for column, week in enumerate(weeks):
        for day in week["contributionDays"]:
            row = day["weekday"]
            level = LEVELS[day["contributionLevel"]]
            x, y = offset + column * step, offset + row * step
            cell_class = ""
            if level:
                path_index = row * len(weeks) + (column if row % 2 == 0 else len(weeks) - column - 1)
                percentage = 100 * path_index / path_steps
                before = max(0, percentage - 0.02)
                after = min(100, percentage + 0.02)
                cell_class = f' class="eat-{column}-{row}"'
                eaten_styles.append(
                    f'@keyframes eat-{column}-{row}{{'
                    f'0%,{before:.3f}%{{fill:{colors[level]};}}'
                    f'{after:.3f}%,100%{{fill:{colors[0]};}}'
                    f'}}.eat-{column}-{row}{{animation:eat-{column}-{row} 28s linear infinite;}}'
                )
            cells.append(
                f'<rect x="{x - 5}" y="{y - 5}" width="11" height="11" '
                f'rx="2" fill="{colors[level]}"{cell_class}/>'
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
        + "".join(eaten_styles)
        + '@media (prefers-reduced-motion:reduce){.snake,[class^="eat-"]{animation:none;}}'
        '</style>'
        + "".join(cells)
        + f'<path class="snake" d="{path}" fill="none" stroke="{snake_color}" '
        'stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>'
        '</svg>\n'
    )


def card(title, body):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 180" '
        'width="420" height="180" role="img">'
        '<rect x="1" y="1" width="418" height="178" rx="12" '
        'fill="#17141f" stroke="#6b3658" stroke-width="2"/>'
        f'<text x="20" y="31" fill="#ff7ab8" font-size="17" '
        f'font-family="Arial, sans-serif" font-weight="bold">{escape(title)}</text>'
        '<path d="M20 43H400" stroke="#6b3658"/>'
        + body
        + '</svg>\n'
    )


def render_stats(user):
    repositories = user["repositories"]
    values = (
        ("Contribuições / ano", user["contributionsCollection"]["contributionCalendar"]["totalContributions"]),
        ("Repositórios públicos", repositories["totalCount"]),
        ("Estrelas recebidas", sum(repo["stargazerCount"] for repo in repositories["nodes"])),
        ("Seguidores", user["followers"]["totalCount"]),
    )
    body = []
    for index, (label, value) in enumerate(values):
        x = 20 + index % 2 * 200
        y = 73 + index // 2 * 54
        body.append(
            f'<text x="{x}" y="{y}" fill="#f6e9f2" font-size="25" '
            f'font-family="Arial, sans-serif" font-weight="bold">{value}</text>'
            f'<text x="{x}" y="{y + 19}" fill="#cbb7c6" font-size="11" '
            f'font-family="Arial, sans-serif">{escape(label)}</text>'
        )
    return card("GitHub em números", "".join(body))


def render_languages(user):
    sizes = defaultdict(int)
    for repo in user["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            sizes[edge["node"]["name"]] += edge["size"]
    ranked = sorted(sizes.items(), key=lambda item: item[1], reverse=True)[:5]
    total = sum(sizes.values())
    if not ranked or not total:
        return card("Linguagens no código público", '<text x="20" y="90" fill="#f6e9f2">Sem dados de linguagens.</text>')
    bars = []
    for index, (name, size) in enumerate(ranked):
        y = 64 + index * 23
        width = round(156 * size / ranked[0][1])
        percentage = round(100 * size / total)
        bars.append(
            f'<text x="20" y="{y}" fill="#f6e9f2" font-size="12" '
            f'font-family="Arial, sans-serif">{escape(name[:15])}</text>'
            f'<rect x="164" y="{y - 10}" width="156" height="11" rx="5" fill="#302637"/>'
            f'<rect x="164" y="{y - 10}" width="{width}" height="11" rx="5" fill="#ff7ab8"/>'
            f'<text x="335" y="{y}" fill="#cbb7c6" font-size="11" '
            f'font-family="Arial, sans-serif">{percentage}%</text>'
        )
    return card("Linguagens no código público", "".join(bars))


def main():
    user = fetch_profile()
    calendar = user["contributionsCollection"]["contributionCalendar"]
    output = Path("dist")
    output.mkdir(exist_ok=True)
    for filename, (snake_color, colors) in PALETTES.items():
        (output / filename).write_text(
            render_snake(calendar, snake_color, colors), encoding="utf-8"
        )
    (output / "github-stats.svg").write_text(render_stats(user), encoding="utf-8")
    (output / "github-languages.svg").write_text(render_languages(user), encoding="utf-8")


if __name__ == "__main__":
    main()
