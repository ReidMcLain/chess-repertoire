# Elementary tactical pattern library

The aim is to recognize a precise relationship between pieces, then calculate enough to verify it. Keep one permanent reference puzzle for each pattern and revisit that exact position. This is a proposed study taxonomy, not a claim that chess has one universally agreed classification. Descriptive leaf labels below are training labels; traditional names are identified where useful.

## Resources that fit this approach

**ChessTempo is the closest platform fit.** It supports a hierarchical motif system, modifiers identifying the executing piece and whether the move checks, and personal tags. Its premium features include custom sets, spaced repetition and sorted sets that can be looped. These let you maintain a fixed collection and add finer classifications yourself. Automatic/community tags still need review before a puzzle becomes your reference example. See the [tag system announcement](https://chesstempo.com/blog/27/new-tactics-tagging-system) and [training feature description](https://chesstempo.com/blog/24/tactical-motif-solving-now-free).

For elementary curated content, consider Peter Giannatos's **Everyone's First Chess Workbook**, covering fundamental tactics and checkmates with deliberately clean exercises. Select a manageable subset by exercise number and repeat it. It supplies the positions; your index can supply the finer labels. [Publisher description](https://www.newinchess.com/everyone-s-first-chess-workbook).

Within the Chess King ecosystem, **Chess Tactics for Beginners** is worth checking before moving further into CT-ART. Chess King's guide places beginner material across its early learning levels, including 600–1200. This is a course-level guide, not an interchangeable online puzzle rating. [Publisher's level guide](https://blog.chessking.com/guide/peshka/).

## Vocabulary: what each word does

These are working definitions for consistent study. Authors sometimes use “motif,” “theme,” and “combination” differently.

| Term | Working meaning |
| --- | --- |
| Tactics | Concrete play exploiting immediate opportunities or solving immediate threats. |
| Tactic | A particular operation: for example, checking and then winning a rook. |
| Tactical motif/theme | A recurring idea that helps explain the operation, such as a pin or deflection. |
| Tactical vulnerability | A feature making an operation possible: exposed king, loose queen, overloaded defender. |
| Pattern | A recognizable arrangement or relationship among pieces and squares. |
| Mechanism | What the moves accomplish: remove a guard, open a line, create two threats. |
| Combination | A coordinated tactical sequence toward a concrete result; many traditional definitions emphasize sacrifice. |
| Sacrifice | Giving up material for compensation; its soundness must be established. |
| Sham/pseudo-sacrifice | A temporary material investment with a concrete recovery or forced payoff. |
| Positional sacrifice | Material investment justified by lasting advantages rather than immediate recovery. |
| Objective | Mate, material gain, promotion, a draw, or escaping a threat. |
| Candidate move | A plausible move selected for calculation. |
| Forcing move | A move sharply restricting useful replies. A check is not automatically the best move. |
| Threat | What you intend to accomplish next if it is not prevented. |
| Tempo | A move's worth of time; attacking something valuable can gain one. |
| Initiative | The ability to set threats or problems the opponent must address. |
| Calculation | Examining concrete continuations and evaluating their endpoints. |
| Visualization | Keeping the changing position accurate in your head. |
| Board vision | Noticing attacks, defenses, legal moves and piece relationships. |
| Pattern recognition | Recognizing a familiar arrangement and retrieving a likely idea. |
| Move order | The sequence in which operations must occur. |
| Main line | The principal continuation being examined. |
| Variation | Another continuation, often an alternative defense. |
| Refutation | A reply showing why a proposed move or line fails. |
| Counterplay | Active chances created by the defender. |
| Zwischenzug/intermezzo | An inserted move before an expected action, often a recapture. |
| Zwischencheck | An intermediate move that gives check. |
| Quiet move | In this library, a move without check or capture; record its threat separately because source definitions vary. |
| Forcing sequence | A line in which threats tightly constrain the replies; each defense still needs checking. |
| Mating net | Coordinated control restricting the king and enabling mate. |
| Flight square/luft | An escape square for the king; luft commonly means space created by a pawn move. |
| En prise | Available to be captured; this alone does not establish that the capture is good. |
| Hanging/loose piece | An undefended piece; distinguish “loose” from actually capturable without a tactical penalty. |
| Underdefended piece | A piece whose defenses are insufficient in the concrete exchange sequence. |
| The exchange | The material difference between a rook and a bishop or knight. |
| Desperado | A doomed or tactically expendable piece taking material or creating a threat before it is lost. |
| Poisoned piece/pawn | An apparently available capture that permits an unfavorable reply. |
| Swindle | A practical resource giving an opponent chances to spoil a superior position. |
| Stalemate | The side to move has no legal move and is not in check. |
| Perpetual check | A repeatable checking mechanism used to secure a draw; it is not itself a separate formal draw rule. |
| Zugzwang | Having to move worsens the position. |
| Domination | Restricting a piece so all its useful routes are controlled. |

The distinction between a general tactic and an actual sequence is illustrated in [Chess.com's tactics guide](https://www.chess.com/terms/chess-tactics). For the inserted-move mechanism see [Zwischenzug](https://www.chess.com/terms/zwischenzug-chess).

## Family tree

The tree supplies navigation. Attributes supply additional precision without duplicating a position in dozens of branches. A puzzle can have several mechanisms, but designate the one the exercise is intended to teach.

```text
TACTICAL PATTERNS
├── Material and basic board vision
│   ├── Undefended target → pawn / knight / bishop / rook / queen
│   ├── Underdefended target → favorable capture sequence on one square
│   ├── Exchange counting → unequal values / move order / multiple squares
│   └── Apparently defended target → pinned guard / overloaded guard
├── Multiple threats
│   ├── Fork: the same piece attacks multiple targets
│   │   ├── Knight
│   │   │   ├── King + queen (royal fork)
│   │   │   ├── King + rook
│   │   │   ├── King + bishop / knight
│   │   │   ├── Queen + rook
│   │   │   ├── Two rooks
│   │   │   ├── Queen + bishop / knight
│   │   │   └── Three or more targets
│   │   ├── Pawn → two minors / minor + rook / two majors / king + piece
│   │   ├── Bishop → king + rook / king + queen / two non-king targets
│   │   ├── Rook → king + queen / king + piece / rank-and-file targets
│   │   ├── Queen → check + loose piece / check + pawn / two loose pieces
│   │   └── King → two safely capturable targets in an endgame
│   └── Other double threats
│       ├── Mate threat + material threat
│       ├── Promotion threat + material threat
│       ├── Two separate mating threats
│       └── Two attackers create separate threats with one move
├── Line relationships
│   ├── Pin
│   │   ├── Absolute: leaving the line exposes one's king to check
│   │   ├── Relative: leaving exposes valuable material
│   │   ├── Restriction by mate threat: moving permits mate
│   │   └── Exploitation → attack pinned piece / exploit ineffective guard
│   ├── Skewer
│   │   ├── King in front → queen / rook / minor behind
│   │   ├── Queen in front → rook / minor behind
│   │   └── Rook in front → minor behind
│   ├── Discovery
│   │   ├── Discovered attack → departing piece checks
│   │   ├── Discovered attack → departing piece captures
│   │   ├── Discovered attack → departing piece creates another threat
│   │   ├── Discovered check → departing piece captures material
│   │   ├── Discovered check → departing piece improves position
│   │   └── Double check → king must move
│   └── X-ray → pressure through a blocker / defense after exchanges
├── Manipulating defenders and targets
│   ├── Capture the defender: remove the guarding piece
│   ├── Deflection: make the defender leave its duty
│   ├── Decoy/attraction: bring a target to a useful square
│   ├── Overloading: exploit incompatible defensive duties
│   ├── Interference: interrupt an enemy defensive line
│   ├── Clearance → square / file / rank / diagonal
│   ├── Line opening → pawn exchange / pawn sacrifice / piece sacrifice
│   ├── Blockade/obstruction: deny an important square or route
│   └── Destruction of king shelter: remove protective pawns
├── Trapping and restricting
│   ├── Trapped queen / rook / bishop / knight
│   ├── Net tightened by a pawn move
│   ├── Escape square removed with tempo
│   └── Domination of a short-range or badly placed piece
├── Move order and forcing play
│   ├── Zwischenzug → check / capture / threat
│   ├── Countercheck: answer check with a legal checking move
│   ├── Desperado capture → material / check / promotion
│   ├── Quiet mating threat
│   └── Zugzwang → mating net / material loss / pawn ending
├── Promotion
│   ├── Direct promotion → safe queen / promotion with check
│   ├── Pawn breakthrough → deflection / clearance / sacrifice
│   ├── Remove or distract blockader
│   ├── Knight underpromotion → fork / check / mate
│   ├── Rook or bishop underpromotion → avoid stalemate
│   └── Promotion with discovered attack or check
├── Defensive tactics and draws
│   ├── Capture attacker / move target / add defender / interpose
│   ├── Exchange attacking piece
│   ├── Counterthreat → check / mate threat / material
│   ├── Perpetual check / perpetual attack
│   ├── Stalemate → sacrifice last mobile piece / block own moves
│   ├── Simplification to a drawn ending
│   └── Fortress: a positional drawing structure, cross-listed here
├── Named combinations
│   ├── Windmill: alternating direct and discovered checks
│   ├── Repeated knight-fork harvesting (separate from classic windmill)
│   ├── Greek gift: bishop sacrifice on h7/h2 with a conditional attack
│   ├── Légal combination: queen offered, minor pieces deliver mate
│   └── Philidor's legacy: a combination producing smothered mate
└── Mating patterns → see the table below
```

A partial pin allows movement along the pin line; it is an attribute, not an alternative to “absolute” or “relative.” A pawn can be pinned and a king can fork. A checking fork still fails if the forking piece can be captured safely or the second target can escape through a forcing reply.

For deflection, ask “which duty was abandoned?” For attraction, ask “which destination was induced?” A single move can do both. Overloading describes the conflicting duties that make such an operation work. See [deflection examples](https://www.chess.com/terms/deflection-chess).

## Forks: the required granularity

Every fork reference card should store these independent dimensions:

| Dimension | Examples |
| --- | --- |
| Executing piece | Knight, pawn, bishop, rook, queen, king |
| Targets | King–queen, king–rook, queen–rook, rook–rook, bishop–knight |
| Forcing character | Checking fork; non-checking fork |
| Entry | Immediately available; capture onto fork square; promotion onto fork square |
| Preparation | Decoy target; deflect guard; capture guard; clear square; clear route; pin guard |
| Geometry | Central knight outpost; back-rank targets; queen diagonal check plus lateral attack |
| Target safety | Loose; defended but profitably capturable; guard disabled |
| Counterplay | Can capture forker; countercheck; mate threat; both threats answered together |
| Outcome | Win queen; win exchange; win minor; win pawn; force draw |

Example leaf: **Knight → king–queen → checking fork → decoy-created → queen won**. “Royal fork” names the targets, not how the position was created. “Family fork” is used inconsistently; prefer an explicit three-target list.

## Mating-pattern lexicon

Group by visual mechanism and then by traditional name. Study the final diagram first; learning a name does not require calculating a long sacrificial setup.

| Family | Pattern | Recognition cue |
| --- | --- | --- |
| Heavy pieces | Back-rank mate | A rook or queen checks along the home rank; escape is blocked. |
| Heavy pieces | Ladder/lawnmower mate | Two heavy pieces alternate cutting off and checking the king. |
| Heavy pieces | King and queen box | Queen restricts the king; own king supports the finish. |
| Heavy pieces | King and rook box | Rook cuts off; own king restricts the remaining flights. |
| Rook + knight | Anastasia's mate | Knight covers two exits; enemy piece plugs another; rook checks along the edge. |
| Rook + knight | Arabian mate | Knight protects the adjacent mating rook and controls a flight. |
| Knight | Smothered mate | Knight checks a king boxed in by its own pieces. |
| Bishops | Boden's mate | Crossing bishop diagonals close around a king obstructed by its own army. |
| Bishops | Double-bishop mate | Bishops control neighboring diagonals; remaining flights are unavailable. |
| Rook + bishop | Opera mate | Bishop supports the rook delivering mate on the back rank. |
| Rook + bishop | Morphy's mate | Bishop checks; rook cuts off escapes beside the cornered king. |
| Rook + bishop | Pillsbury's mate | Rook checks; bishop supplies diagonal escape control. |
| Queen geometry | Epaulette mate | Own pieces occupy squares beside the king, like shoulder ornaments. |
| Queen geometry | Dovetail mate | Protected adjacent diagonal queen; two rear diagonal flights occupied. |
| Queen geometry | Swallow's-tail mate | Protected adjacent orthogonal queen; two rear diagonal flights occupied. |
| Opening patterns | Scholar's mate | Queen mates on f7/f2 with bishop support. |
| Opening patterns | Fool's mate | Early diagonal access to a king whose pawn moves weakened its shelter. |
| Combination endpoint | Légal's mate | Two knights and a bishop coordinate after the queen is offered. |

The geometry and naming can overlap. See [Chess.com's illustrated mate reference](https://www.chess.com/terms/checkmate-chess) and the complementary [Lichess mate themes](https://lichess.org/training/themes). The distinction between Anastasia and Arabian is particularly useful: in Arabian, the knight protects the mating rook. [Arabian explanation](https://www.chess.com/terms/arabian-mate-chess).

Further named patterns to add after these diagrams are familiar: **Greco, Damiano, Lolli, Blackburne, hook, Vuković, Balestra, blind swine, kill box, triangle, and corner mate**. These require their own reference diagrams before their labels become useful. This is a broad practical lexicon, not an exhaustive dictionary of composition themes or every historical naming variant.

## A fixed Woodpecker routine

The essential repetition is the same selected exercises through successive cycles. The original method describes repeated passes; the smaller numbers below are my proposed adaptation for elementary recognition, not the book's prescribed schedule. [Publisher excerpt](https://www.qualitychess.co.uk/ebooks/WoodpeckerMethod-excerpt.pdf).

1. Start with **24–40 positions**, selected for clarity rather than a nominal rating cutoff. Keep their permanent IDs.
2. For each leaf pattern, learn one anchor position and explain the cue aloud: “the knight can check the king and attack the queen.”
3. Solve the fixed set over several sessions. Finish each line and identify why the opponent's relevant alternatives fail.
4. Repeat the same positions in the next cycle. Record first-attempt accuracy and time separately. Do not replace an awkward puzzle just because you missed it.
5. Revisit misses after other puzzles have intervened, then include them in the next full cycle.
6. Hide names and theme labels during mixed testing. Keep names visible in the learning browser and solution explanation.
7. Once you recognize the anchors accurately, add a few unseen examples of each pattern. This tests whether the relationship transfers beyond the memorized square coordinates.

Start with loose pieces, exchange counting, simple checking forks, pin exploitation, and final mate diagrams. Then add one preparatory move: remove a guard, decoy a king, or open a line. Windmill is a named multi-step mechanism, so keep it in a separate introduction block. A windmill consists of repeated checks and discoveries, not merely a single discovered attack. [Windmill explanation](https://www.chess.com/terms/windmill-chess).

## Reference-card specification

Each card needs: permanent ID; precise title; starting FEN and side to move; teaching objective; complete annotated line; relevant alternative defenses and accepted answers; primary family path; secondary mechanisms; visual cue; source/provenance; difficulty label with its scale; and per-cycle attempts, correctness, hints and elapsed time.

An example title is **NF-001 — Knight royal fork: immediate check on d6**. An example mate title is **MA-001 — Anastasia: knight seals g8/g6, rook uses the h-file**. Descriptive titles are library labels, not invented historical names.

The accompanying `anchor-puzzles.pgn` provides a small set of original, deliberately simplified teaching positions with permanent IDs. They have no measured Elo rating. It is a starter set, not coverage of every leaf above. Use a PGN study viewer; the existing repertoire app's one-reply quiz does not provide a complete multi-move tactics workflow.
