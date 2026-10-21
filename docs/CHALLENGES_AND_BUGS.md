# Challenges and bugs

Nineteen real problems from building Parkha, grouped by where they showed up and numbered roughly
in the order I hit them (code comments refer to these numbers). Several were found by the safety
gate rejecting my own code, which is the best evidence I have that it's worth having.

## Getting the data

### 1. I couldn't download the label documents
My build environment blocked direct downloads from ppqs.gov.in and the state agriculture sites
that mirror the CIB&RC PDFs. I read them through a text-extraction reader instead and transcribed
the rows by hand. That's a transcription risk on the most safety-critical data in the project, so
every row in `data/labels.csv` carries its source id, and [RESPONSIBLE_AI.md](RESPONSIBLE_AI.md)
makes a second-person check of every row the first condition for real use.

### 2. The PDF's text stopped at "C"
The insecticide document's text layer ends at Cyantraniliprole, about 65,000 characters in. Emamectin
benzoate, imidacloprid, spinosad and the rest of the alphabet aren't in my table. That changed the
design: Parkha needed a first-class "I don't have a verified waiting period for this" answer, with
no date and no dose, instead of assuming every product would be covered. The lexicon still knows
those names so it can say so (eval d29: spinosad on tomato).

### 3. The Indian label recommends products Nepal has banned
Carbofuran 3% CG is on the Indian label for maize, tomato, potato and eight other crops;
carbosulfan for brinjal; chlorpyrifos for cabbage, brinjal and beans. All three are banned in
Nepal. If options came straight from the label table, Parkha would recommend banned products. The
ban list now overrides the label table everywhere (`LabelBook.options`), and the template answer
names them as banned when they're on the label for the crop asked about ("Do not use carbosulfan
and chlorpyrifos: banned in Nepal").

### 4. The two ban sources disagree on dates
BMC Public Health (2021) lists phorate as banned in 2015; The Kathmandu Post reports phorate in
the December 2024 gazette order alongside chlorpyrifos and paraquat. The 2019 group (carbofuran,
dichlorvos and others) is "2018" in the Post. Nepal's fiscal year 2075 BS runs from July 2018 to
July 2019, which probably explains the second. I kept the earlier year and recorded the later
order in the note column rather than picking one silently.

### 5. "Leaf miner" is two different pests
The only tomato "leaf miner" on the Indian label is *Liriomyza trifolii*. Nepal's tomato problem
is *Tuta absoluta*, the South American tomato leaf miner, a different insect that has developed
resistance. A lexicon that mapped "leaf miner" to one pest would have offered broflanilide for
Tuta on the strength of a Liriomyza label. They are separate pests in the lexicon, options need an
exact pest match, and `test_options_need_the_pest_on_the_label` pins it.

That raised a second question: does the waiting period depend on the pest? It doesn't: it's set
by residue on the crop at that dose. So **dose needs crop and pest to match; the waiting period
only needs the crop**.

### 6. Two waiting periods for neem on tomato
Azadirachtin 1% EC has 3 days on tomato; the 5% extract has 5 days. A farmer with a bottle that
says "neem" doesn't know which formulation it is. Parkha uses the longest waiting period across
a crop's rows. The general rule: when the data is ambiguous, be wrong in the direction of waiting
longer.

## The gate rejecting my own answers

### 7. A template that said "chlorpyrifos" without "banned" in the same sentence
The harvest template for a banned product said "I don't have a verified waiting period for
chlorpyrifos on cabbage..." and then, two sentences later, "Chlorpyrifos has been banned since
2024". The gate checks every sentence that names a banned product for a ban word, and rejected it.
The gate was right: a farmer who stops reading after the first sentence learns about chlorpyrifos's
waiting period, not its ban. The template now leads with the ban and says "it" afterwards.

### 8. Broflanilide was invisible in Nepali answers
The Nepali options answer listed "ब्रोफ्लानिलाइड (१ दिन) ... नीम (३ दिन)". The gate's lexicon only
knew broflanilide's English name, so in that sentence it saw one product, neem, and two waiting
periods, and flagged "neem: 1 day, label says 3". The gate can't check a name it can't read. Every
Nepali display name is now an alias automatically, and a test checks that each product's Nepali
name is recognised.

### 9. नीम (neem) inside रोपनीमा ("per ropani")
Next, every Nepali dose line failed with "azadirachtin was not returned by any tool". Devanagari
aliases matched as substrings so that postpositions work (गोलभेडामा, "in tomato"), and नीम is a
substring of रोपनीमा. Devanagari aliases now have to start a word and may run on after it. This
was a holdout failure (h20).

### 10. "khursani ma thrips" got an English answer
The language detector wanted two romanised-Nepali grammar words, and this question has one ("ma").
A crop name in romanised Nepali (khursani, bhanta, makai...) plus one grammar word now counts.
Also a holdout failure (h13).

### 15. My own example dates failed the number rule
The "tell me when you sprayed" template offered examples: "हिजो, ३ दिन अगाडि, असोज २८". The gate saw
3 and 28, numbers in no tool result, and rejected it. Examples are now words ("yesterday, a few days
ago, or the date").

### 16. Only the last product appeared in Nepali answers
The eval's options check failed on brinjal: the Nepali answer listed one product where the English
listed three. A scripted edit had dedented `parts.append(...)` out of its loop. Plain bug, found
because the eval checks the Nepali answers separately rather than assuming they mirror the English.

## The gate letting wrong answers through

### 11. Neem's 7 days on cabbage excused "7 days" on cauliflower
The mutation test changed neem's 5 days on cauliflower to 7, and the gate passed it. The allowed
waiting periods came from `chemical_status`, which lists a product's waiting period on every crop,
and neem has 7 days on cabbage. The allowed set is now limited to the crops the question is about.

### 12. A x10 dose passed
"2.5 ml per ropani" mutated to "25 ml" passed, because 25 happens to be another figure in the tool
results. Plain number membership can't see a real number in the wrong place (Sodhnus hit the same
thing with rainfall). Doses now have their own rule: a number with ml or g must be one of the rates
returned for the product named just before it. 8/11 to 11/11.

### 13. Two waiting periods swapped inside a list passed, mostly by luck
The waiting-period rule only checked sentences naming exactly one product. Swapping broflanilide's
1 day and chlorantraniliprole's 3 days in a list keeps every number real and present. The English
version was caught anyway, by accident: my sentence splitter breaks on the "." in "2.5 ml", which
happened to put each product in its own fragment. The Nepali one wasn't. Each waiting period is
now attributed to the nearest product named before it in the same sentence.

### 14. "Twice a week" read as a waiting period
A new rule rejects waiting periods in words next to a product ("a couple of days"), because they
can't be checked. It then rejected "check the underside of leaves twice a week" in the diamondback
moth note. A lookbehind excludes "twice/once/times a week".

## The question screen

### 17. "kati khayo bhane marincha" wasn't caught as a crisis
("How much would I have to eat to die?") The romanised pattern "marin" ended with a word boundary,
and "marincha" continues past it. In a crisis check, a miss is the worst kind of error, so the
romanised patterns now match word starts only, and the eval has three crisis questions in three
scripts.

### 18. "My tomato leaves look shiny" was refused
The cosmetic-spraying pattern included "shiny" to catch "make the cauliflower shiny for market",
and caught a farmer describing symptoms instead. Removed; the cosmetic check now needs "fresh"
wording or "before market".

## Data, again

### 19. Units the source didn't print
Two neem rows give a rate ("2500-5000", "200") with no unit I could read reliably. Guessing ml
versus g on a dose is not acceptable, so those rows have a blank unit and Parkha gives their
waiting period but no dose.
