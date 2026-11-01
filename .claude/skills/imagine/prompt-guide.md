# Image prompt guide

`/imagine` reads this file when it writes or improves a prompt. The rules suit gpt-image-1 and Gemini image models.

## Clarifying Questions to Consider

Before producing a prompt, determine:
1. **What is the goal?** — architecture diagram, infographic, conceptual illustration, UI mockup, comparison chart?
2. **Who is the audience?** — developers, executives, general public?
3. **What style?** — technical blueprint, clean infographic, whiteboard sketch, isometric 3D, flat vector?
4. **What level of detail?** — high-overview, detailed technical, simplified metaphor?
5. **Any specific color preferences or branding?**
6. **What format/aspect ratio?** — landscape (1536x1024), portrait (1024x1536), square (1024x1024)?

If the user has given clear answers to most of these, proceed without asking.

---

## Prompt Construction Rules (gpt-image-1 Best Practices)

### Structure (always follow this order)
```
[Use case / diagram type]: [Scene/background]. [Subject with specifics]. [Key details/hierarchy]. [Style/medium]. [Lighting or visual tone]. [Composition/framing]. [Hard constraints].
```

### Rules

**1. Put the most important concept first**
The model weights earlier tokens more heavily. Lead with the diagram type or primary subject.

**2. Be specific, not vague**
- BAD: "nice diagram", "ultra-detailed", "high quality"
- GOOD: "system architecture diagram, flat vector style, white background, blue boxes for services, orange arrows for data flow"

**3. Avoid generic quality words**
Never use: "8K", "ultra HD", "masterpiece", "stunning", "photorealistic" unless photography is the literal goal.
Instead name the specific medium: "technical illustration", "flat vector graphic", "clean infographic style".

**4. Specify visual hierarchy explicitly**
For diagrams, name the components and their relationships:
"Three tiers: blue box labeled 'Kafka' at top, green cylinder labeled 'PostgreSQL' in middle, orange box labeled 'Handler' at bottom, connected by downward arrows with labels"

**5. Use diagramming vocabulary**
Use: "node", "edge", "swimlane", "callout label", "bounding box", "connector line", "legend", "tier", "layer"

**6. Text in the image**
- Always quote text that must appear verbatim: `"subscribe()" in monospace font`
- Spell unusual names letter-by-letter if needed
- Add: "verbatim text rendering, no extra characters"
- Complex text-heavy diagrams: mention `quality=high` in your recommendation

**7. Constraints — always say what to exclude**
End the prompt with: "no watermark, no extra decorative elements, no people" or whatever applies.

**8. Color coding**
Be explicit: "databases in blue (#2563EB), services in green (#16A34A), external systems in gray (#6B7280)"

**9. For comparisons or multi-section diagrams**
Describe each section separately with clear spatial language:
"LEFT HALF shows X... RIGHT HALF shows Y... separated by a vertical dashed line"

**10. Style vocabulary that works well**
- Technical: "flat vector technical diagram", "blueprint style", "Lucidchart-style", "AWS architecture diagram style", "clean whiteboard sketch"
- Illustrative: "isometric 3D render", "modern SaaS marketing illustration", "The Economist infographic style"
- Photography: "professional studio photography, soft-box lighting" (only when appropriate)

---


## Example prompt

**Prompt:**
System architecture diagram, flat vector style, white background. Two columns side by side separated by a vertical dashed gray line. LEFT COLUMN labeled "subscribe()" in bold: Kafka box in blue at top connected by downward arrow labeled "poll()" to App box, then single arrow to Database cylinder and Handler box shown side by side labeled "store + process inline". RIGHT COLUMN labeled "inbox_subscribe()" in bold: Kafka box in blue connected to App box connected to Database cylinder labeled "store only"; below a dashed horizontal separator labeled "separate task", Database cylinder connected to App box connected to Handler box labeled "poll + process". Each box has its label centered in 11pt monospace. Color legend at bottom: blue=Kafka/consumer, green=database, orange=handler. No watermark, no decorative icons, no people.

**Settings:** `size=1536x1024`, `quality=high`
