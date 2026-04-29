# Workflow evaluation: rows 26-100

## Evaluation basis

- Source: `results.json`
- Rows: 26-100 of NLTK WordNet synsets sorted by `synset.name()`
- Workflows compared: `agent-baseline`, `agent-multiphase`, `agent-conceptual`
- Ollama/backend use: none
- Criteria: literal coverage, sense fidelity, natural Serbian, POS fit, gloss quality, curator risk

## Aggregate literal coverage

| Workflow | Total literals | Avg literals / synset | Single-literal rows | Confidence profile |
|---|---:|---:|---:|---|
| `agent-baseline` | 127 | 1.69 | 23/75 | 49 high, 26 medium |
| `agent-multiphase` | 245 | 3.27 | 0/75 | 49 high, 26 medium |
| `agent-conceptual` | 146 | 1.95 | 5/75 | 49 high, 26 medium |

## Full literal comparison

| # | Synset | Baseline literals | Multiphase literals | Conceptual literals |
|---:|---|---|---|---|
| 26 | `a-horizon.n.01` | A-horizont | A-horizont; povrsinski horizont tla; humusni horizont | A-horizont; gornji horizont tla |
| 27 | `a-line.n.01` | A-linija | A-kroj; odeca A-kroja; haljina A-kroja | odeca A-kroja; A-kroj |
| 28 | `a-list.n.01` | A-lista | A-lista; lista povlascenih osoba; lista prioritetnih osoba | A-lista; lista posebno favorizovanih osoba |
| 29 | `a-ok.s.01` | u redu; ispravan | sve u redu; besprekorno; u savrsenom stanju | u savrsenom redu; besprekoran |
| 30 | `a-scan_ultrasonography.n.01` | A-sken ultrasonografija | A-sken ultrasonografija; A-sken ultrazvucni pregled; ultrazvucno merenje duzine ocne jabucice | A-sken ultrasonografija; ultrazvucno merenje oka |
| 31 | `a-team.n.01` | A-tim | A-tim; elitni tim; grupa elitnih vojnika; vodeci savetnicki tim | elitni tim; A-tim |
| 32 | `a.n.06` | A; slovo A | slovo A; A; prvo slovo latinice | slovo A; prvo slovo rimske abecede |
| 33 | `a.n.07` | krvna grupa A; tip A | krvna grupa A; tip A; grupa A | krvna grupa A; grupa A |
| 34 | `a_battery.n.01` | A-baterija | A-baterija; baterija za grejanje vlakana vakuumske cevi | A-baterija |
| 35 | `a_bit.r.01` | malo; pomalo | malo; pomalo; donekle; neznatno | malo; u maloj meri |
| 36 | `a_cappella.r.01` | a kapela; bez pratnje | a kapela; bez instrumentalne pratnje; bez muzicke pratnje | a kapela; bez instrumentalne pratnje |
| 37 | `a_cappella.s.01` | a kapela | a kapela; pevan bez instrumentalne pratnje; bez instrumentalne pratnje | a kapela; bez instrumentalne pratnje |
| 38 | `a_cappella_singing.n.01` | a kapela pevanje | a kapela pevanje; pevanje bez instrumentalne pratnje; pevanje bez pratnje | pevanje bez instrumentalne pratnje; a kapela pevanje |
| 39 | `a_few.s.01` | nekoliko; par | nekoliko; par; mali broj | nekoliko; vise od jednog |
| 40 | `a_fortiori.r.01` | a fortiori; tim pre | tim pre; utoliko pre; sa jos jacim razlogom; a fortiori | tim pre; sa jos jacim razlogom |
| 41 | `a_kempis.n.01` | Tomas a Kempis; a Kempis | Toma Kempijski; Tomas a Kempis; Thomas a Kempis | Toma Kempijski; Thomas a Kempis |
| 42 | `a_la_carte.a.01` | a la carte | a la carte; po jelovniku; sa odvojenom cenom za svako jelo | a la carte; po jelovniku |
| 43 | `a_la_carte.n.01` | a la carte meni | a la carte meni; jelovnik sa pojedinacnim cenama; meni po jelovniku | a la carte meni; jelovnik sa odvojenim cenama |
| 44 | `a_la_carte.r.01` | a la carte; po jelovniku | a la carte; po jelovniku; narucivanjem pojedinacnih jela | po jelovniku; a la carte |
| 45 | `a_la_mode.r.01` | a la mode; sa sladoledom | sa sladoledom; uz sladoled; a la mode | sa sladoledom; uz sladoled |
| 46 | `a_level.n.01` | A-level; A-nivo | A-level; A-nivo; napredni nivo skolskog predmeta | A-level; ispit A-nivoa |
| 47 | `a_lot.r.01` | mnogo; veoma | mnogo; veoma; u velikoj meri; znatno | mnogo; u veoma velikoj meri |
| 48 | `a_posteriori.a.01` | a posteriori; empirijski | a posteriori; empirijski; zasnovan na iskustvu; induktivan | a posteriori; zasnovan na cinjenicama |
| 49 | `a_posteriori.r.01` | a posteriori; iz iskustva | a posteriori; na osnovu opazenih cinjenica; iz iskustva | a posteriori; empirijski |
| 50 | `a_posteriori.s.01` | a posteriori; empirijski | a posteriori; koji zahteva dokaz; empirijski proverljiv | a posteriori; zasnovan na dokazima |
| 51 | `a_priori.a.01` | a priori; apriorni | a priori; apriorni; deduktivan | apriorni; a priori |
| 52 | `a_priori.r.01` | a priori; apriorno | a priori; apriorno; deduktivno; bez opazenih cinjenica | apriorno; a priori |
| 53 | `a_priori.s.01` | a priori; apriorni | a priori; apriorni; teorijski; hipoteticki | teorijski; apriorni |
| 54 | `aa.n.01` | aa lava; aa | aa lava; hrapava lava; skoriasta lava | aa lava; hrapava lava |
| 55 | `aachen.n.01` | Ahen; Aachen | Ahen; Aachen; Aix-la-Chapelle | Ahen; Aachen |
| 56 | `aalborg.n.01` | Olborg; Aalborg | Olborg; Aalborg; Alborg | Olborg; Aalborg |
| 57 | `aalii.n.01` | aalii | aalii; havajsko drvo aalii; Dodonaea | aalii; malo havajsko drvo |
| 58 | `aalst.n.01` | Alst; Aalst | Alst; Aalst; grad Alst | Alst; Aalst |
| 59 | `aalto.n.01` | Aalto; Alvar Aalto | Alvar Aalto; Aalto; Hugo Alvar Henrik Aalto | Alvar Aalto; Aalto |
| 60 | `aardvark.n.01` | africki mravojed; aardvark | africki mravojed; aardvark; mravlji medved; Orycteropus afer | africki mravojed; Orycteropus afer |
| 61 | `aardwolf.n.01` | zemljani vuk; aardwolf | zemljani vuk; aardwolf; Proteles cristata; prugasta hijena | zemljani vuk; Proteles cristata |
| 62 | `aare.n.01` | Aare; reka Aare | Aare; Aar; reka Aare | reka Aare; Aare |
| 63 | `aaron.n.01` | Hank Aaron; Henry Louis Aaron | Hank Aaron; Henry Louis Aaron; Henri Luis Aron | Hank Aaron; Henri Luis Aron |
| 64 | `aaron.n.02` | Aron | Aron; biblijski Aron; Mojsijev stariji brat | Aron |
| 65 | `ab.n.02` | av; ab | av; ab; mesec av | mesec av; av |
| 66 | `ab.n.04` | krvna grupa AB; tip AB | krvna grupa AB; tip AB; grupa AB | krvna grupa AB; grupa AB |
| 67 | `aba.n.01` | aba | aba; arapski ogrtac bez rukava; labavi spoljasnji ogrtac | aba; arapski ogrtac |
| 68 | `aba.n.02` | aba | aba; tkanina aba; tkanina od kozje i kamilje dlake | aba; aba tkanina |
| 69 | `abaca.n.02` | abaka; manilska konoplja | abaka; manilska konoplja; Musa textilis | abaka; manilska konoplja |
| 70 | `abacinate.v.01` | abacinirati | abacinirati; oslepiti usijanim metalom; oslepiti usijanom plocom | oslepiti usijanom plocom; abacinirati |
| 71 | `aback.r.01` | sa jedrima okrenutim protiv vetra | protiv vetra na jedrima; sa vetrom na prednjoj strani jedara; unazad pod vetrom | sa jedrima pritisnutim s prednje strane |
| 72 | `aback.r.02` | zateceno; iznenadjeno | zateceno; iznenadjeno; nespremno | zateceno; iznenadjeno |
| 73 | `abactinal.a.01` | abaktinalan | abaktinalan; suprotan ustima; na povrsini nasuprot ustima | abaktinalan; nasuprot oralnoj strani |
| 74 | `abacus.n.01` | abakus | abakus; kapitelna ploca; ploca na vrhu kapitela | abakus; ploca kapitela |
| 75 | `abacus.n.02` | abakus; racunaljka | abakus; racunaljka; racunska tabla | abakus; racunaljka |
| 76 | `abadan.n.01` | Abadan | Abadan; grad Abadan; luka Abadan | Abadan |
| 77 | `abalone.n.01` | abalon; morsko uvo | abalon; morsko uvo; Haliotis | abalon; morsko uvo |
| 78 | `abampere.n.01` | abamper; abamp | abamper; abamp; jedinica struje od 10 ampera | abamper |
| 79 | `abandon.n.01` | nesputanost; neobuzdanost | nesputanost; neobuzdanost; razuzdanost; sloboda bez kocnica | nesputanost; neobuzdanost |
| 80 | `abandon.v.01` | napustiti; ostaviti | napustiti; ostaviti; ostaviti za sobom | napustiti; ostaviti |
| 81 | `abandon.v.02` | odreci se; napustiti | odreci se; prepustiti; napustiti zahtev; dati se | odreci se; prepustiti |
| 82 | `abandon.v.04` | odustati; napustiti | odustati; napustiti; odreci se; prestati insistirati | odustati od; napustiti tvrdnju |
| 83 | `abandon.v.05` | napustiti; ostaviti | napustiti; ostaviti na cedilu; izneveriti; dezertirati | ostaviti na cedilu; napustiti |
| 84 | `abandoned.s.01` | napusten; pust | napusten; ostavljen; pust; zapusten | napusten; pust |
| 85 | `abandoned.s.02` | nesputan; neobuzdan | nesputan; neobuzdan; razuzdan | nesputan; slobodan od stega |
| 86 | `abandoned_person.n.01` | napustena osoba | napustena osoba; otpisana osoba; osoba za koju je napustena nada | osoba bez nade; napustena osoba |
| 87 | `abandoned_ship.n.01` | napusteni brod | napusteni brod; brod bez posade; derelikt | napusteni brod; brod napusten na pucini |
| 88 | `abandonment.n.01` | napustanje; odricanje | napustanje; odustajanje; odricanje; desertiranje | odustajanje; napustanje |
| 89 | `abandonment.n.03` | odricanje; napustanje prava | dobrovoljno odricanje; napustanje prava; odricanje od imovine | dobrovoljno odricanje od imovine; napustanje prava |
| 90 | `abarticulation.n.01` | iscasenje zgloba; abartikulacija | iscasenje zgloba; luksacija; abartikulacija | iscasenje zgloba; luksacija |
| 91 | `abasement.n.01` | ponizenje; unizenje | ponizenje; unizenje; degradacija; ponizeno stanje | ponizenost; ponizenje |
| 92 | `abashed.s.01` | postidjen; posramljen | postidjen; posramljen; zbunjen; nelagodno samosvestan | posramljen; postidjen |
| 93 | `abashment.n.01` | posramljenost; stidljivost | posramljenost; stid; stidljivost | stidljivost; posramljenost |
| 94 | `abasia.n.01` | abazija; nemogucnost hodanja | abazija; nemogucnost hodanja; nesposobnost hoda | abazija; nemogucnost hodanja |
| 95 | `abasia_trepidans.n.01` | tremorna abazija | tremorna abazija; abazija usled drhtanja nogu; abasia trepidans | tremorna abazija; abazija sa drhtanjem nogu |
| 96 | `abasic.a.01` | abazijski; abazican | abazijski; abazican; koji se odnosi na abaziju | abazijski; vezan za abaziju |
| 97 | `abatable.s.01` | umanjiv; otklonjiv | umanjiv; otklonjiv; koji se moze ublaziti; koji se moze suzbiti | otklonjiv; koji se moze umanjiti |
| 98 | `abatable_nuisance.n.01` | otklonjiva smetnja | otklonjiva smetnja; otklonjiva neprijatnost; smetnja koja se moze suzbiti | otklonjiva smetnja; smetnja koja se moze otkloniti |
| 99 | `abate.v.02` | jenjavati; smanjiti se | jenjavati; popustiti; smanjiti se; utihnuti; slabiti | jenjavati; popustiti; smanjivati se |
| 100 | `abatement.n.02` | smanjenje; ublazavanje | smanjenje; ublazavanje; suzbijanje; umanjenje | smanjenje; ublazavanje |

## Main findings

- `agent-baseline` remains conservative and readable, but it under-generates for technical, taxonomic, proper-name, and legal/medical entries.
- `agent-multiphase` is again the strongest evaluation workflow because it consistently exposes alternate Serbian literals and descriptive candidates.
- `agent-conceptual` gives the cleanest final-entry shape for many rows, especially where literal translation is awkward, but it often suppresses useful alternates.
- Proper names and specialized domains need curator confirmation: `Aalborg`, `Aalst`, `aalii`, `aardwolf`, `abactinal`, `abatable nuisance`, and medical Latin terms are the riskiest rows.
- For common vocabulary rows such as `a bit`, `a few`, `a lot`, `abandon`, `abandoned`, and `abate`, all three workflows are broadly aligned; multiphase is best for exposing nuance.

## Workflow strengths and weaknesses

### `agent-baseline`

Strengths: quick, conservative, low risk of over-expansion, good for control comparison and obvious proper-name preservation.

Weaknesses: not enough literals for evaluation, often leaves borrowed labels without Serbian descriptive alternatives, and can miss domain-specific natural forms.

### `agent-multiphase`

Strengths: best candidate coverage, best for curator review, and strongest at showing both borrowed/proper-name forms and natural Serbian descriptions.

Weaknesses: includes some borderline candidates that require filtering; descriptive phrases can be too broad to serve as strict WordNet literals.

### `agent-conceptual`

Strengths: strongest gloss quality and usually best representative literal; especially helpful for distinguishing senses such as architecture `abacus` vs calculator `abacus`.

Weaknesses: lower synonym coverage than multiphase; sometimes omits alternates that are useful for evaluation.

## Recommendation

Use `agent-multiphase` as the candidate-pool generator, `agent-conceptual` as the final gloss/representative selector, and `agent-baseline` as the control column. For the full 117k+ WordNet set, continue in bounded batches with the same report structure.
