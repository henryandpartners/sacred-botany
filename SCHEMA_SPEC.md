# Sacred Botany — Plant Profile Authoring Spec

You are authoring entries for **Sacred Botany**, a single-page atlas of psychoactive,
medicinal and ritual plants, fungi and brews. For EACH species in your input file,
produce exactly ONE JavaScript object that matches the schema below.

## Workflow
1. Read this spec (`SCHEMA_SPEC.md`).
2. Read your input file (path given in the task) — a JSON array of
   `{ "sci", "compounds", "image" }`.
3. For each species, write one object per the schema, using accurate botanical and
   pharmacological knowledge. The scientific name is your anchor — derive the common
   name, family, native range and everything else from it.
4. Write ALL objects as ONE valid JavaScript array to the output file (path given in
   the task), e.g. `[{...}, {...}]`.
5. Your FINAL message must be a SHORT confirmation only: how many entries you wrote and
   any species you were unsure about. Do NOT paste the array into your final message.

## Hard rules
- Output must be **syntactically valid JavaScript**: double-quoted strings, proper
  commas, NO trailing commas, NO markdown, NO comments, NO code fences.
- Use the provided `image` URL **verbatim**. Write a fitting `alt` (short image
  description, e.g. "Piper methysticum (kava) shrub").
- `compounds`: render the provided compound list as a JS array of strings.
- Be **accurate and measured**. It is fine to describe traditional and ceremonial use.
  If the modern pharmacological evidence is weak or limited, say so plainly.
- **Never invent** specific studies, clinical trial numbers, precise doses, or citations.
  Keep pharmacology to well-established mechanisms.
- `safety` and `legality` must be honest — include "status varies by jurisdiction;
  check local law" and "consult a qualified professional" where relevant.
- `id` must be snake_case derived from the scientific name (lowercase, spaces →
  underscores, diacritics removed) and unique across your batch.

## Schema (every field required, in this order)
```
{
  id:          string   // snake_case from sci
  name:        string   // most widely accepted common name
  sci:         string   // scientific name (as given)
  family:      string   // botanical family (add a short clarifier if useful)
  form:        string   // one phrase: tree / shrub / herb / vine / fungus / bark … + key feature
  continent:   string   // primary continent or "Pancontinental" / "Boreal" / "Tropical"
  regions:     string[] // 2–6 specific native countries/regions
  coords:      [number, number]  // [lat, lon] of a representative native location
  habitat:     string   // one line
  image:       string   // provided URL, verbatim
  alt:         string   // short image description
  parts:       string   // the part used (root, bark, leaf, seed, whole plant, …)
  compounds:   string[] // provided list
  pharmacology: string  // 1–3 sentences, evidence-honest
  id_features: string[] // 3–5 short field-identification bullets
  lookalikes:  string[] // 2–4 bullets: confusable species or "distinctive, few lookalikes"
  prep: {
    summary:   string   // one sentence
    steps:     string[] // 2–5 concrete preparation steps
    note:      string   // one line (social/ritual/safety nuance of the prep)
  },
  culture: {
    cultures:  string[] // 2–5 peoples / traditions (with local name in parens if known)
    ritual:    string   // how and when it is used ceremonially
    context:   string   // one line of cultural significance
  },
  legality:    string   // one honest line
  safety:      string   // one honest line (toxicity, interactions, contraindication)
}
```

## Reference example — match this shape and tone exactly
```
{
  id:"kava", name:"Kava", sci:"Piper methysticum",
  family:"Piperaceae", form:"Aromatic shrub", continent:"Oceania",
  regions:["Fiji","Vanuatu","Tonga","Samoa","Hawai'i","Across Melanesia & Micronesia"], coords:[-17.8,178.0],
  habitat:"Tropical, moist lowlands near water",
  image:"https://upload.wikimedia.org/wikipedia/commons/8/83/Starr_040318-0058_Piper_methysticum.jpg",
  alt:"Piper methysticum (kava) shrub",
  parts:"The rhizome / root",
  compounds:["Kavalactones"],
  pharmacology:"Kavalactones act on GABA-A receptors (the same target as benzodiazepines) and modulate calcium channels — producing sedation, anxiolysis and muscle relaxation, without classic 'psychedelic' visuals.",
  id_features:[
    "A 1–2 m shrub with glossy, dark-green, heart-shaped leaves.",
    "Small, inconspicuous flower clusters (it rarely flowers outside its native range).",
    "Strongly aromatic stems, leaves and — above all — the rhizome.",
    "The pungent, aromatic root is the part that is prepared and shared."
  ],
  lookalikes:[
    "Distinguish from other peppery Pipers by the strongly aromatic rhizome.",
    "A cultivated crop across the Pacific; the root, not the leaf, is the medicine.",
    "One of the most widely shared ritual substances on Earth."
  ],
  prep:{
    summary:"The root is grated and kneaded with water into a shared, earthy brown drink.",
    steps:[
      "The rhizome is cut and grated or pounded.",
      "It is placed in a bowl and mixed with water.",
      "The pulp is kneaded by hand (or through a strainer) to release the kavalactones.",
      "The resulting liquid is sipped from a shared bowl (tanoa / yago), passed around the circle."
    ],
    note:"Preparation is itself a social act — the kneading and sharing are part of the ceremony."
  },
  culture:{
    cultures:["Fijian ('yaqona')","Tongan ('kava')","Samoan","Hawaiian ('kava')","Many Melanesian & Micronesian peoples"],
    ritual:"Central to Pacific social and ceremonial life: welcoming guests, honouring chiefs, settling disputes, and religious observance. The bowl is passed in a set order; taking kava is a mark of respect, kinship and community.",
    context:"A unifying cultural institution of the Pacific — a 'liquid of ceremony'."
  },
  legality:"A legal traditional beverage in most of the Pacific and widely elsewhere.",
  safety:"Generally mild; heavy long-term use has been linked to liver strain — avoid combining with alcohol."
},
```

## Self-check before you finish
- [ ] One object per input species, all 19 top-level fields present (prep and culture nested).
- [ ] The output file is a single valid JS array (would pass `node -e "eval(...)"` style parse).
- [ ] `id`s unique and snake_case.
- [ ] No fabricated studies, doses or citations.
- [ ] `image` URLs copied verbatim from the input.
