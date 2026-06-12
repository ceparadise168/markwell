"""A built-in sample library — public-domain texts, no real user data.

Shown on first run / empty states so someone can see what reading their
highlights will feel like *before* plugging in a Kobo, and so screenshots and
tests never touch anyone's personal data. Everything here is public domain
(Marcus Aurelius, Thoreau, Austen, 老子, 夏目漱石, 김소월) and includes CJK
text on purpose, to prove the reading view renders Chinese, Japanese, and
Korean as beautifully as English.
"""
from __future__ import annotations

from ..model import Book, Highlight


def library() -> list[Book]:
    """Return the sample books, mirroring what `reader.read_books()` produces."""
    return [
        Book(
            title="Meditations",
            author="Marcus Aurelius",
            volume_id="sample:meditations",
            highlights=[
                Highlight(
                    "When you arise in the morning, think of what a precious "
                    "privilege it is to be alive — to breathe, to think, to "
                    "enjoy, to love.",
                    date="2024-01-08", chapter_index=2),
                Highlight(
                    "You have power over your mind — not outside events. "
                    "Realize this, and you will find strength.",
                    note="Came back to this on a hard week. The whole book in "
                         "one line.",
                    date="2024-01-22", chapter_index=2),
                Highlight(
                    "The happiness of your life depends upon the quality of "
                    "your thoughts.",
                    date="2024-02-03", chapter_index=5),
                Highlight(
                    "Waste no more time arguing about what a good man should "
                    "be. Be one.",
                    date="2024-03-19", chapter_index=10),
                Highlight(
                    "Very little is needed to make a happy life; it is all "
                    "within yourself, in your way of thinking.",
                    date="2024-04-11", chapter_index=7),
            ],
        ),
        Book(
            title="Walden",
            author="Henry David Thoreau",
            volume_id="sample:walden",
            highlights=[
                Highlight(
                    "I went to the woods because I wished to live "
                    "deliberately, to front only the essential facts of life.",
                    note="The reason I started keeping highlights at all.",
                    date="2024-05-02", chapter_index=2),
                Highlight(
                    "The mass of men lead lives of quiet desperation.",
                    date="2024-05-09", chapter_index=1),
                Highlight(
                    "Rather than love, than money, than fame, give me truth.",
                    date="2024-06-15", chapter_index=18),
                Highlight(
                    "Our life is frittered away by detail. Simplify, simplify.",
                    date="2024-07-01", chapter_index=2),
            ],
        ),
        Book(
            title="Pride and Prejudice",
            author="Jane Austen",
            volume_id="sample:pride",
            highlights=[
                Highlight(
                    "It is a truth universally acknowledged, that a single man "
                    "in possession of a good fortune, must be in want of a wife.",
                    date="2025-01-12", chapter_index=1),
                Highlight(
                    "I could easily forgive his pride, if he had not mortified "
                    "mine.",
                    date="2025-01-20", chapter_index=5),
                Highlight(
                    "You must allow me to tell you how ardently I admire and "
                    "love you.",
                    note="Mr. Darcy, finally.",
                    date="2025-02-14", chapter_index=34),
            ],
        ),
        Book(
            title="道德經",
            author="老子",
            volume_id="sample:daodejing",
            highlights=[
                Highlight(
                    "道可道，非常道；名可名，非常名。",
                    date="2025-03-03", chapter_index=1),
                Highlight(
                    "知人者智，自知者明。勝人者有力，自勝者強。",
                    note="自勝者強——最難的是勝過自己。",
                    date="2025-03-18", chapter_index=33),
                Highlight(
                    "合抱之木，生於毫末；九層之臺，起於累土；千里之行，始於足下。",
                    date="2025-04-07", chapter_index=64),
                Highlight(
                    "天下莫柔弱於水，而攻堅強者莫之能勝，以其無以易之。",
                    date="2025-05-21", chapter_index=78),
            ],
        ),
        Book(
            title="草枕",
            author="夏目漱石",
            volume_id="sample:kusamakura",
            highlights=[
                Highlight(
                    "山路を登りながら、こう考えた。",
                    date="2025-06-05", chapter_index=1),
                Highlight(
                    "智に働けば角が立つ。情に棹させば流される。意地を通せば窮屈だ。",
                    note="何度読んでも身につまされる。",
                    date="2025-06-18", chapter_index=1),
                Highlight(
                    "とかくに人の世は住みにくい。",
                    date="2025-07-02", chapter_index=1),
            ],
        ),
        Book(
            title="진달래꽃",
            author="김소월",
            volume_id="sample:jindallaekkot",
            highlights=[
                Highlight(
                    "나 보기가 역겨워 가실 때에는 말없이 고이 보내 드리우리다",
                    date="2025-08-03", chapter_index=1),
                Highlight(
                    "가시는 걸음 걸음 놓인 그 꽃을 사뿐히 즈려밟고 가시옵소서",
                    date="2025-08-06", chapter_index=1),
                Highlight(
                    "나 보기가 역겨워 가실 때에는 죽어도 아니 눈물 흘리우리다",
                    note="교과서에서 배울 때는 몰랐던 슬픔이 이제야 보인다.",
                    date="2025-08-10", chapter_index=1),
            ],
        ),
    ]
