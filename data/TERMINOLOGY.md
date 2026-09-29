# Terminology Glossary

Standard Myanmar/English technical terms for consistent dataset labeling and model output.
Use these terms consistently across all books during QC review.

## Core Programming

| English | Standard term (use in output) | Notes |
|---------|------------------------------|-------|
| variable | variable / ကြေညာတဲ့အရာ | Prefer "variable" in code context |
| function | function | Keep English keyword in code |
| parameter | parameter / ပါရာမီတာ | |
| return | return | Code keyword stays English |
| loop | loop / for loop | Use "loop" or "for loop" in code context |
| array | array / စာရင်း | |
| list | list / စာရင်း | Python list |
| odd number | မ ဂဏန်း / မဂဏန်း | Not တစ်တန်း |
| even number | စုံ ဂဏန်း | |
| modulo / remainder | modulo / အကြွင်း | e.g. `%` operator |
| range | range | Keep `range()` in code |
| append | append | Keep `append()` in code |
| iterate | iterate / တစ်ခုချင်း စစ် | |
| object | object / object | |
| class | class | OOP term |
| method | method | |
| string | string / string | |
| integer | integer / ကိန်းပြည့် | |
| boolean | boolean / true-false | |
| condition | condition / အခြေအနေ | if/else context |
| operator | operator / operator | |
| syntax | syntax | |
| debug | debug / error ရှာဖွေခြင်း | |
| compile | compile | |
| runtime | runtime | |

## Web Development

| English | Standard term | Notes |
|---------|---------------|-------|
| HTML | HTML | |
| CSS | CSS | |
| JavaScript | JavaScript | |
| DOM | DOM | |
| API | API | |
| REST | REST API | |
| HTTP | HTTP | |
| request | request / တောင်းဆိုမှု | |
| response | response / တုံ့ပြန်မှု | |
| endpoint | endpoint | |
| JSON | JSON | |
| AJAX | AJAX | |
| component | component | React context |
| props | props | React |
| state | state | React |
| hook | hook | React hooks |
| route | route | Laravel/routing |
| middleware | middleware | Laravel |
| migration | migration | Laravel DB |
| Eloquent | Eloquent | Laravel ORM |
| blade | Blade template | Laravel |
| bootstrap | Bootstrap | CSS framework |
| grid | grid / grid system | |
| responsive | responsive design | |
| column (layout) | column / တန်း | **တစ်တန်း** = one column in grid only |
| row (layout) | row | Not "တစ်တန်း" for math |

## Disambiguation (do not mix)

| Phrase | Use only when |
|--------|----------------|
| တစ်တန်း / နှစ်တန်း | Bootstrap/grid/responsive **columns**, not odd/even numbers |
| မ ဂဏန်း | `i % 2`, odd numbers in a list |
| စာရင်း | Python list / array storage |

## Database

| English | Standard term | Notes |
|---------|---------------|-------|
| database | database / ဒေတာဘေ့စ် | |
| table | table / ဇယား | |
| row | row / 행 | |
| column | column / column | |
| primary key | primary key | |
| foreign key | foreign key | |
| query | query / query | |
| SELECT | SELECT | SQL keyword |
| INSERT | INSERT | SQL keyword |
| UPDATE | UPDATE | SQL keyword |
| DELETE | DELETE | SQL keyword |
| JOIN | JOIN | SQL keyword |
| index | index | |
| normalization | normalization | |

## PHP Specific

| English | Standard term |
|---------|---------------|
| array | array |
| associative array | associative array |
| superglobal | superglobal |
| session | session |
| cookie | cookie |
| form | form |
| POST | POST |
| GET | GET |

## Usage Rules

1. **Code keywords** stay in English inside code blocks.
2. **Explanations** use Myanmar with English terms where standard (e.g., "function", "variable").
3. Do not mix random transliterations — pick one style per term and stick to it.
4. Tag samples with `terms` field listing which glossary entries appear.
5. Never use **တစ်တန်း** for odd numbers or list storage.
