"""A built-in sample library — public-domain texts, no real user data.

Shown on first run / empty states so someone can see what reading their
highlights will feel like *before* plugging in a Kobo, and so screenshots and
tests never touch anyone's personal data. Everything here is public domain
(Marcus Aurelius, Thoreau, Austen, 老子) and includes CJK text on purpose, to
prove the reading view renders Chinese as beautifully as English.
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
                    "天下莫柔弱於水，而攻堅強者莫之能勝，以其無以易之。",
                    date="2025-04-07", chapter_index=78),
                Highlight(
                    "合抱之木，生於毫末；九層之臺，起於累土；千里之行，始於足下。",
                    date="2025-05-21", chapter_index=64),
            ],
        ),
    ]
