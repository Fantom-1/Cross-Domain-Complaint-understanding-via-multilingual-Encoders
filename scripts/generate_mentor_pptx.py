"""Generate executive 16:9 widescreen PowerPoint presentation (.pptx)
for the Cross-Domain Complaint Understanding (CDCU) final delivery.
"""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
import os

def create_presentation(output_path: str):
    prs = Presentation()
    # 16:9 widescreen dimensions
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_slide_layout = prs.slide_layouts[6]

    # Color Palette - Professional Minimalist Monochrome & Accents
    BG_COLOR = RGBColor(255, 255, 255)
    CARD_BG = RGBColor(248, 249, 250)
    CARD_BORDER = RGBColor(226, 232, 240)
    TEXT_MAIN = RGBColor(17, 24, 39)
    TEXT_MUTED = RGBColor(100, 116, 139)
    TEXT_SUBTLE = RGBColor(148, 163, 184)
    ACCENT_BLACK = RGBColor(15, 23, 42)
    ACCENT_GREEN = RGBColor(5, 150, 105)      # +gains
    GREEN_BG = RGBColor(236, 253, 245)
    GREEN_BORDER = RGBColor(167, 243, 208)
    ACCENT_BLUE = RGBColor(29, 78, 216)       # MRR
    ACCENT_PURPLE = RGBColor(126, 34, 206)    # NDCG
    ACCENT_RED = RGBColor(220, 38, 38)

    def add_header(slide, tag_text: str, title_text: str, subtitle_text: str = None):
        # Header container
        top_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.733), Inches(1.1))
        tf = top_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        # Small tag
        p_tag = tf.paragraphs[0]
        p_tag.text = tag_text.upper()
        p_tag.font.name = "Arial"
        p_tag.font.size = Pt(9)
        p_tag.font.bold = True
        p_tag.font.color.rgb = TEXT_MUTED

        # Main Title
        p_title = tf.add_paragraph()
        p_title.text = title_text
        p_title.font.name = "Arial"
        p_title.font.size = Pt(22)
        p_title.font.bold = True
        p_title.font.color.rgb = TEXT_MAIN

        if subtitle_text:
            p_sub = tf.add_paragraph()
            p_sub.text = subtitle_text
            p_sub.font.name = "Arial"
            p_sub.font.size = Pt(11)
            p_sub.font.color.rgb = TEXT_MUTED

    def add_card(slide, left, top, width, height, bg_color=CARD_BG, border_color=CARD_BORDER):
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        shape.fill.solid()
        shape.fill.fore_color.rgb = bg_color
        shape.line.color.rgb = border_color
        shape.line.width = Pt(1)
        return shape

    # =========================================================================
    # SLIDE 1: Title Slide
    # =========================================================================
    slide1 = prs.slides.add_slide(blank_slide_layout)
    
    # Title badge
    badge = slide1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.0), Inches(2.2), Inches(0.35))
    badge.fill.solid()
    badge.fill.fore_color.rgb = RGBColor(241, 245, 249)
    badge.line.color.rgb = RGBColor(203, 213, 225)
    b_tf = badge.text_frame
    b_tf.margin_top = Inches(0.05)
    bp = b_tf.paragraphs[0]
    bp.alignment = PP_ALIGN.CENTER
    bp.text = "FINAL MENTOR SUBMISSION"
    bp.font.size = Pt(8.5)
    bp.font.bold = True
    bp.font.color.rgb = RGBColor(51, 65, 85)

    # Main Project Title
    t_box = slide1.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.733), Inches(2.5))
    ttf = t_box.text_frame
    ttf.word_wrap = True
    tp1 = ttf.paragraphs[0]
    tp1.text = "Cross-Domain Complaint Understanding"
    tp1.font.name = "Arial"
    tp1.font.size = Pt(38)
    tp1.font.bold = True
    tp1.font.color.rgb = TEXT_MAIN

    tp2 = ttf.add_paragraph()
    tp2.text = "via Multilingual Foundation Encoders"
    tp2.font.name = "Arial"
    tp2.font.size = Pt(34)
    tp2.font.bold = True
    tp2.font.color.rgb = ACCENT_BLUE

    tp3 = ttf.add_paragraph()
    tp3.text = "Overcoming Representation Anisotropy in 778.5M Parameter XLM-V via Parallel Deep Contrastive Learning"
    tp3.font.name = "Arial"
    tp3.font.size = Pt(14)
    tp3.font.color.rgb = TEXT_MUTED

    # Highlights Row (4 Stat Cards)
    stats = [
        ("PRECISION@10", "48.97%", "+34.86% over baseline", ACCENT_GREEN),
        ("MRR@10", "0.5619", "+72.4% relative gain", ACCENT_BLUE),
        ("NDCG@10", "0.4889", "+226.6% relative gain", ACCENT_PURPLE),
        ("DATASET", "45,723", "CFPB FOIA across 9 domains", ACCENT_BLACK)
    ]
    card_w = Inches(2.75)
    gap = Inches(0.24)
    start_x = Inches(0.8)
    for i, (label, val, sub, col) in enumerate(stats):
        x = start_x + i * (card_w + gap)
        add_card(slide1, x, Inches(4.3), card_w, Inches(1.6))
        tb = slide1.shapes.add_textbox(x + Inches(0.2), Inches(4.45), card_w - Inches(0.4), Inches(1.3))
        stf = tb.text_frame
        stf.word_wrap = True
        
        p_lbl = stf.paragraphs[0]
        p_lbl.text = label
        p_lbl.font.size = Pt(9.5)
        p_lbl.font.bold = True
        p_lbl.font.color.rgb = TEXT_MUTED

        p_val = stf.add_paragraph()
        p_val.text = val
        p_val.font.size = Pt(24)
        p_val.font.bold = True
        p_val.font.color.rgb = col

        p_sub = stf.add_paragraph()
        p_sub.text = sub
        p_sub.font.size = Pt(9)
        p_sub.font.color.rgb = TEXT_MUTED

    # Bottom Metadata Strip
    meta_box = slide1.shapes.add_textbox(Inches(0.8), Inches(6.3), Inches(11.733), Inches(0.6))
    mtf = meta_box.text_frame
    mp = mtf.paragraphs[0]
    mp.text = "Repository: Fantom-1/Cross-Domain-Complaint-understanding-via-multilingual-Encoders   |   Branch: feature/contrastive-retrieval-engine   |   Unit Tests: 162/162 Passed (100%)"
    mp.font.size = Pt(9.5)
    mp.font.color.rgb = TEXT_SUBTLE

    # =========================================================================
    # SLIDE 2: The Core Problem - Representation Anisotropy Crisis
    # =========================================================================
    slide2 = prs.slides.add_slide(blank_slide_layout)
    add_header(slide2, "The Research Challenge", "Representation Anisotropy in Multilingual Foundation Models",
               "Why large language models fail at legal and financial grievance retrieval out-of-the-box.")

    # Left Card: The Failure Mode
    add_card(slide2, Inches(0.8), Inches(1.7), Inches(5.7), Inches(5.0))
    tb_l = slide2.shapes.add_textbox(Inches(1.1), Inches(1.9), Inches(5.1), Inches(4.5))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True

    p = tf_l.paragraphs[0]
    p.text = "1. The Vector Collapse Failure Mode"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = TEXT_MAIN

    p = tf_l.add_paragraph()
    p.text = "When raw pretrained foundation models like facebook/xlm-v-base are applied to consumer complaints without domain adaptation, embeddings collapse into a narrow, high-density cone:"
    p.font.size = Pt(11)
    p.font.color.rgb = TEXT_MUTED

    p = tf_l.add_paragraph()
    p.text = "• Average Unrelated Cosine: cos(θ) ≈ 0.962 (Representation Collapse)\n" \
             "• Pretrained XLM-V Precision@10: 14.11%\n" \
             "• Standard Lexical TF-IDF: 33.54%\n" \
             "• Baseline Deficit: The 778M parameter neural model trails keyword search by -19.43%."
    p.font.size = Pt(11)
    p.font.color.rgb = TEXT_MAIN

    p = tf_l.add_paragraph()
    p.text = "Root Cause: High-resource language subwords and statutory boilerplate words crowd the representation space, rendering unadapted euclidean and cosine metrics uninformative."
    p.font.size = Pt(10)
    p.font.color.rgb = TEXT_MUTED

    # Right Card: The Solution
    add_card(slide2, Inches(6.8), Inches(1.7), Inches(5.7), Inches(5.0))
    tb_r = slide2.shapes.add_textbox(Inches(7.1), Inches(1.9), Inches(5.1), Inches(4.5))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True

    p = tf_r.paragraphs[0]
    p.text = "2. The Contrastive Metric Solution"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = ACCENT_GREEN

    p = tf_r.add_paragraph()
    p.text = "Contrastive representation learning maps complaints onto a normalized hypersphere S^(d-1), enforcing three geometric properties:"
    p.font.size = Pt(11)
    p.font.color.rgb = TEXT_MUTED

    p = tf_r.add_paragraph()
    p.text = "• Alignment: Semantically equivalent grievances map to identical coordinates regardless of surface phrasing.\n" \
             "• Uniformity: Embeddings spread uniformly across all dimensions, preserving maximal entropy and information content.\n" \
             "• Margin Separation: Unrelated grievance categories (e.g. debt harassment vs mortgage escrow) are separated by an enforced angular margin α."
    p.font.size = Pt(11)
    p.font.color.rgb = TEXT_MAIN

    p = tf_r.add_paragraph()
    p.text = "Outcome: Overcomes statutory boilerplate bias and elevates retrieval Precision@10 from 14.11% to 48.97%."
    p.font.size = Pt(10.5)
    p.font.bold = True
    p.font.color.rgb = ACCENT_GREEN

    # =========================================================================
    # SLIDE 3: Architecture Deep-Dive: XLM-V 778.5M Reality
    # =========================================================================
    slide3 = prs.slides.add_slide(blank_slide_layout)
    add_header(slide3, "Foundation Architecture", "XLM-V: The 778.5M Parameter Architecture Reality",
               "Why literature calls it the '~1 Billion parameter model' and how the neural layers are allocated.")

    # 3 Stat Cards Across
    c_w = Inches(3.7)
    c_gap = Inches(0.3)
    start_c = Inches(0.8)
    arch_stats = [
        ("VOCABULARY SCALE", "901,629", "Meta AI's 140+ language subword table (vs 250k in XLM-RoBERTa and 30k in RoBERTa)."),
        ("EMBEDDING MATRIX", "692.8 Million", "901,629 x 768 = 692,848,128 parameters. 89.0% of entire model footprint!"),
        ("TRANSFORMER BACKBONE", "85.1 Million", "12 Transformer layers (12 heads, 768 hidden, 3,072 FFN) + position embeddings.")
    ]
    for i, (ttl, num, desc) in enumerate(arch_stats):
        x = start_c + i * (c_w + c_gap)
        add_card(slide3, x, Inches(1.7), c_w, Inches(2.2))
        tb = slide3.shapes.add_textbox(x + Inches(0.2), Inches(1.85), c_w - Inches(0.4), Inches(1.9))
        tf = tb.text_frame
        tf.word_wrap = True
        p1 = tf.paragraphs[0]
        p1.text = ttl
        p1.font.size = Pt(9.5)
        p1.font.bold = True
        p1.font.color.rgb = TEXT_MUTED

        p2 = tf.add_paragraph()
        p2.text = num
        p2.font.size = Pt(24)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_MAIN

        p3 = tf.add_paragraph()
        p3.text = desc
        p3.font.size = Pt(10)
        p3.font.color.rgb = TEXT_MUTED

    # Bottom Explanation Card
    add_card(slide3, Inches(0.8), Inches(4.2), Inches(11.733), Inches(2.5))
    tb_b = slide3.shapes.add_textbox(Inches(1.1), Inches(4.35), Inches(11.1), Inches(2.1))
    tf_b = tb_b.text_frame
    tf_b.word_wrap = True

    p = tf_b.paragraphs[0]
    p.text = "Architectural Breakdown & Projection Head Design"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = TEXT_MAIN

    p = tf_b.add_paragraph()
    p.text = "1. The 1B Model Reality: Standard base models have ~110M–125M parameters. Meta AI's massive 901k vocabulary causes the embedding table alone to take 692.8M parameters, requiring high-memory GPU infrastructure (24GB Blackwell MIG slices) for backpropagation.\n" \
             "2. Non-Linear Metric Projection Head: To project 768-dim pooled representations into an optimal hyperspherical metric space:\n" \
             "    h = MeanPool(H_last) ∈ R^768  →  Linear(768, 768) + GELU  →  Linear(768, 256)  →  L2 Normalization  →  z_norm ∈ S^255\n" \
             "3. Inference Efficiency: 256-dimensional L2-normalized float32 vectors enable exact inner-product nearest-neighbor search across 32,019 cases in under 10 milliseconds."
    p.font.size = Pt(10.5)
    p.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 4: Data Pipeline & Zero-Leakage Splitting
    # =========================================================================
    slide4 = prs.slides.add_slide(blank_slide_layout)
    add_header(slide4, "Data Engineering & Partition Hygiene", "Corpus Provenance, Parsing & Zero-Leakage Splitting",
               "How 45,723 CFPB records were cleaned, clustered, and partitioned without data leakage.")

    # 4 Workflow Steps in Cards
    col_w = Inches(2.75)
    gap_w = Inches(0.24)
    start_col = Inches(0.8)
    steps = [
        ("STAGE 1: SOURCE PROVENANCE", "CFPB FOIA Archive",
         "• Source: CCDB Export 2 (May 2018–Apr 2021)\n• 45,723 canonical instances\n• SHA-256: b591ba980a99...\n• Bureau metadata: 17 U.S.C. § 105 (Public Domain)\n• Narratives: 80 FR 15572 (Consumer Opt-In Consent)"),
        ("STAGE 2: ROBUST PARSING", "Multi-Line Cleaning",
         "• Custom CSV quote-balancing parser\n• Handles embedded CRLF & BOM\n• sys.maxsize field limits\n• De-identification: collapses X{2,} to <REDACTED>\n• Strict 18-column canonical schema"),
        ("STAGE 3: DEDUPLICATION", "Atomic Clustering",
         "• MinHash LSH & exact fingerprinting\n• 3,273 multi-item duplicate clusters (6,546 rows)\n• 39,177 singleton instances\n• Zero Group Leakage: All duplicate cluster items stay in same split"),
        ("STAGE 4: FROZEN SPLITS", "Reconciled Partitions",
         "• Train Set: 32,019 rows (70.03%)\n  SHA-256: febbb253...\n• Validation: 6,852 rows (14.98%)\n  SHA-256: db270bbb...\n• Locked Test: 6,852 rows (14.98%)\n  SHA-256: ffff21c8...")
    ]
    for i, (stage, ttl, details) in enumerate(steps):
        x = start_col + i * (col_w + gap_w)
        add_card(slide4, x, Inches(1.7), col_w, Inches(5.0))
        tb = slide4.shapes.add_textbox(x + Inches(0.18), Inches(1.9), col_w - Inches(0.36), Inches(4.6))
        tf = tb.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = stage
        p1.font.size = Pt(8.5)
        p1.font.bold = True
        p1.font.color.rgb = TEXT_MUTED

        p2 = tf.add_paragraph()
        p2.text = ttl
        p2.font.size = Pt(13)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_MAIN

        p3 = tf.add_paragraph()
        p3.text = details
        p3.font.size = Pt(9.5)
        p3.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 5: Methodology 1: Unsupervised SimCSE
    # =========================================================================
    slide5 = prs.slides.add_slide(blank_slide_layout)
    add_header(slide5, "Contrastive Methodology 1", "Unsupervised SimCSE: Self-Contrastive Learning",
               "Using standard dropout perturbations to uncollapse representations with zero human labels.")

    add_card(slide5, Inches(0.8), Inches(1.7), Inches(5.7), Inches(5.0))
    tb_l = slide5.shapes.add_textbox(Inches(1.1), Inches(1.9), Inches(5.1), Inches(4.5))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True

    p = tf_l.paragraphs[0]
    p.text = "How SimCSE Works Without Labels"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = TEXT_MAIN

    p = tf_l.add_paragraph()
    p.text = "1. Minimal Data Augmentation: Feed a single complaint text x_i through the transformer encoder twice.\n" \
             "2. Random Dropout Perturbation: Because dropout (p=0.1) randomly zeroes out different neural units in each forward pass, the model produces two slightly distinct vectors (z_i, z_i^+).\n" \
             "3. Objective: Treat (z_i, z_i^+) as positive views of the exact same story. Treat all other mini-batch complaints {z_j} as negative pairs.\n" \
             "4. Dropout InfoNCE Loss Formula (τ = 0.05):"
    p.font.size = Pt(10.5)
    p.font.color.rgb = TEXT_MUTED

    p = tf_l.add_paragraph()
    p.text = "L_SimCSE = -log [ exp(sim(z_i, z_i+) / τ) / Σ exp(sim(z_i, z_j+) / τ) ]"
    p.font.size = Pt(10.5)
    p.font.bold = True
    p.font.color.rgb = ACCENT_BLUE

    p = tf_l.add_paragraph()
    p.text = "Theoretical Role: Forces representations to spread uniformly across the unit hypersphere, destroying representation collapse without requiring manual annotations."
    p.font.size = Pt(10)
    p.font.color.rgb = TEXT_MUTED

    # Right Card: SimCSE Training & Results
    add_card(slide5, Inches(6.8), Inches(1.7), Inches(5.7), Inches(5.0))
    tb_r = slide5.shapes.add_textbox(Inches(7.1), Inches(1.9), Inches(5.1), Inches(4.5))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True

    p = tf_r.paragraphs[0]
    p.text = "Empirical Convergence & Results (Run R2)"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = TEXT_MAIN

    p = tf_r.add_paragraph()
    p.text = "• Hardware Allocation: Dedicated Blackwell MIG Slice 0 (1g.24gb, 15.2 GB VRAM)\n" \
             "• Batch Size & Precision: Batch size 16, bfloat16, gradient checkpointing\n" \
             "• Convergence Cadence: Early stopped at Step 1,750 / 10,000 (~0.9 epochs)\n" \
             "• Final Training Loss: 5.58 x 10^-6   |   Eval Loss: 0.0056\n" \
             "• Precision@10: 27.24% (+13.13% absolute gain over Frozen XLM-V)\n" \
             "• MRR@10: 0.4725 (+45.0% relative gain over Frozen)\n" \
             "• NDCG@10: 0.2829 (+89.0% relative gain over Frozen)"
    p.font.size = Pt(10.5)
    p.font.color.rgb = TEXT_MAIN

    p = tf_r.add_paragraph()
    p.text = "Finding: SimCSE rapidly resolves representation anisotropy and doubles zero-shot performance. However, because it lacks class supervision, it cannot form discrete statutory legal boundaries."
    p.font.size = Pt(10)
    p.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 6: Methodology 2: Supervised Contrastive Learning (SupCon)
    # =========================================================================
    slide6 = prs.slides.add_slide(blank_slide_layout)
    add_header(slide6, "Contrastive Methodology 2 (Winner)", "Supervised Contrastive Learning: Category Metric Margins",
               "Leveraging administrative routing tags to learn compact intra-class clusters and wide inter-domain margins.")

    add_card(slide6, Inches(0.8), Inches(1.7), Inches(5.7), Inches(5.0))
    tb_l = slide6.shapes.add_textbox(Inches(1.1), Inches(1.9), Inches(5.1), Inches(4.5))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True

    p = tf_l.paragraphs[0]
    p.text = "How SupCon Learns Statutory Categories"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = ACCENT_GREEN

    p = tf_l.add_paragraph()
    p.text = "1. Supervised Pair Mining: Pull together distinct complaints written by different consumers sharing the same grievance intent (x_i, x_p).\n" \
             "2. Hard Negative Repulsion: Push away complaints belonging to different financial product domains (x_i, x_n) using an angular metric margin.\n" \
             "3. Margin Triplet Metric Loss Formulation (α = 0.2, τ = 0.07):"
    p.font.size = Pt(10.5)
    p.font.color.rgb = TEXT_MUTED

    p = tf_l.add_paragraph()
    p.text = "L_SupCon = max(0, ||z_i - z_p||_2^2 - ||z_i - z_n||_2^2 + α)"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = ACCENT_GREEN

    p = tf_l.add_paragraph()
    p.text = "Theoretical Role: Directly optimizes the hyperspherical metric space so that cosine similarity directly reflects statutory legal relevance rather than surface keyword overlap."
    p.font.size = Pt(10)
    p.font.color.rgb = TEXT_MUTED

    # Right Card: SupCon Training & Results
    add_card(slide6, Inches(6.8), Inches(1.7), Inches(5.7), Inches(5.0))
    tb_r = slide6.shapes.add_textbox(Inches(7.1), Inches(1.9), Inches(5.1), Inches(4.5))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True

    p = tf_r.paragraphs[0]
    p.text = "Deep Training & Empirical Breakthrough (Run R4)"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = ACCENT_GREEN

    p = tf_r.add_paragraph()
    p.text = "• Hardware Allocation: Dedicated Blackwell MIG Slice 1 (1g.24gb, 15.2 GB VRAM)\n" \
             "• Multi-Epoch Depth: Trained for 9,505 steps (into Epoch 5)\n" \
             "• Loss Trajectory: Val loss dropped 4.01 → 3.61 → 3.48 → 3.16 → 2.6954\n" \
             "• Final Training Loss: 1.6175   |   Best Val Loss: 2.6954\n" \
             "• Precision@10: 48.97% (+34.86% over baseline, 3.47x gain!)\n" \
             "• MRR@10: 0.5619 (+72.4% relative gain over Frozen)\n" \
             "• NDCG@10: 0.4889 (+226.6% relative gain over Frozen; +40.8% over TF-IDF)\n" \
             "• vs Keyword TF-IDF: Beats keyword search by +15.43% P@10!"
    p.font.size = Pt(10.5)
    p.font.color.rgb = TEXT_MAIN

    p = tf_r.add_paragraph()
    p.text = "Outcome: Promoted as primary production engine under Protocol Rule 13.10."
    p.font.size = Pt(10.5)
    p.font.bold = True
    p.font.color.rgb = ACCENT_GREEN

    # =========================================================================
    # SLIDE 7: Complete Head-to-Head Comparison Table
    # =========================================================================
    slide7 = prs.slides.add_slide(blank_slide_layout)
    add_header(slide7, "Comparative Evaluation", "Comprehensive Benchmark Matrix Across All Models",
               "Validation benchmark evaluated on 6,852 queries against 32,019 training gallery cases.")

    # Table
    rows = 5
    cols = 7
    t_left = Inches(0.8)
    t_top = Inches(1.8)
    t_width = Inches(11.733)
    t_height = Inches(4.5)

    table_shape = slide7.shapes.add_table(rows, cols, t_left, t_top, t_width, t_height)
    table = table_shape.table

    # Column Widths
    table.columns[0].width = Inches(2.3)
    table.columns[1].width = Inches(1.5)
    table.columns[2].width = Inches(1.4)
    table.columns[3].width = Inches(1.4)
    table.columns[4].width = Inches(1.3)
    table.columns[5].width = Inches(1.9)
    table.columns[6].width = Inches(1.933)

    headers = ["Model Run / Objective", "Precision@10", "MRR@10", "NDCG@10", "Recall@10", "% Gain vs Frozen", "% Gain vs TF-IDF"]
    for j, h in enumerate(headers):
        cell = table.cell(0, j)
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(241, 245, 249)
        p = cell.text_frame.paragraphs[0]
        p.text = h
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = TEXT_MAIN

    data = [
        ("R1: Pretrained Frozen XLM-V", "14.11%", "0.3260", "0.1497", "0.0007", "Baseline (0%)", "-57.9% P@10"),
        ("R0: Lexical TF-IDF Baseline", "33.54%", "0.5458", "0.3472", "0.0017", "+137.7% P@10", "Baseline (0%)"),
        ("R2: Unsupervised SimCSE", "27.24%", "0.4725", "0.2829", "0.0014", "+93.1% P@10", "-18.8% P@10"),
        ("R4: Weakly Supervised SupCon", "48.97%", "0.5619", "0.4889", "0.0025", "+247.1% (3.47x)", "+46.0% (+15.4%)")
    ]
    for i, row in enumerate(data):
        for j, val in enumerate(row):
            cell = table.cell(i + 1, j)
            if i == 3:  # SupCon Winner row
                cell.fill.solid()
                cell.fill.fore_color.rgb = GREEN_BG
            p = cell.text_frame.paragraphs[0]
            p.text = val
            p.font.size = Pt(10.5)
            if i == 3:
                p.font.bold = True
                if j in (1, 5, 6):
                    p.font.color.rgb = ACCENT_GREEN
                elif j == 2:
                    p.font.color.rgb = ACCENT_BLUE
                elif j == 3:
                    p.font.color.rgb = ACCENT_PURPLE
                else:
                    p.font.color.rgb = TEXT_MAIN
            else:
                p.font.color.rgb = TEXT_MAIN

    # Bottom Callout
    c_box = slide7.shapes.add_textbox(Inches(0.8), Inches(6.5), Inches(11.733), Inches(0.5))
    ctf = c_box.text_frame
    cp = ctf.paragraphs[0]
    cp.text = "Decision Rule 13.10 Triggered: SupCon officially promoted as production engine after exceeding both frozen and keyword baselines on MRR (+0.0161) and NDCG (+0.1417) with 100% query coverage."
    cp.font.size = Pt(10)
    cp.font.bold = True
    cp.font.color.rgb = ACCENT_GREEN

    # =========================================================================
    # SLIDE 8: Locked Test Set Evaluation
    # =========================================================================
    slide8 = prs.slides.add_slide(blank_slide_layout)
    add_header(slide8, "Scientific Verification & Hygiene", "Official Locked Test Set Evaluation (Evaluated Once)",
               "Confirming out-of-sample generalizability and verifying zero data leakage.")

    # 4 Cards
    t_stats = [
        ("TEST PRECISION@10", "48.61%", "Δ vs Val: -0.36%", ACCENT_GREEN),
        ("TEST MRR@10", "0.5628", "Δ vs Val: +0.09%", ACCENT_BLUE),
        ("TEST NDCG@10", "0.4864", "Δ vs Val: -0.25%", ACCENT_PURPLE),
        ("TEST QUERIES", "6,852", "100.0% Query Coverage", ACCENT_BLACK)
    ]
    for i, (ttl, num, sub, col) in enumerate(t_stats):
        x = start_x + i * (card_w + gap)
        add_card(slide8, x, Inches(1.8), card_w, Inches(1.8))
        tb = slide8.shapes.add_textbox(x + Inches(0.2), Inches(1.95), card_w - Inches(0.4), Inches(1.5))
        tf = tb.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = ttl
        p1.font.size = Pt(9.5)
        p1.font.bold = True
        p1.font.color.rgb = TEXT_MUTED

        p2 = tf.add_paragraph()
        p2.text = num
        p2.font.size = Pt(26)
        p2.font.bold = True
        p2.font.color.rgb = col

        p3 = tf.add_paragraph()
        p3.text = sub
        p3.font.size = Pt(9.5)
        p3.font.color.rgb = TEXT_MUTED

    # Proof Box
    add_card(slide8, Inches(0.8), Inches(4.0), Inches(11.733), Inches(2.7), bg_color=GREEN_BG, border_color=GREEN_BORDER)
    tb_p = slide8.shapes.add_textbox(Inches(1.1), Inches(4.2), Inches(11.1), Inches(2.3))
    tf_p = tb_p.text_frame
    tf_p.word_wrap = True

    p = tf_p.paragraphs[0]
    p.text = "Zero Data Leakage Audit Findings"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = ACCENT_GREEN

    p = tf_p.add_paragraph()
    p.text = "1. Strict Protocol Adherence: The test split (data/processed/baseline_test.csv, 6,852 rows) remained completely locked throughout all hyperparameter tuning, model design, and architecture selection. It was unlocked and evaluated exactly once.\n" \
             "2. Generalization Verification: The test score (48.61% P@10) aligns with the validation score (48.97% P@10) within 0.36%, while MRR remains stable (+0.09%). This tiny delta proves the model learned generalized semantic manifolds rather than memorizing training instances.\n" \
             "3. Atomic Cluster Proof: MinHash cluster grouping successfully isolated all 3,273 duplicate clusters, guaranteeing zero duplicate group overlap across partitions."
    p.font.size = Pt(11)
    p.font.color.rgb = RGBColor(6, 78, 59)

    # =========================================================================
    # SLIDE 9: Grounded Structured Grievance Summarizer
    # =========================================================================
    slide9 = prs.slides.add_slide(blank_slide_layout)
    add_header(slide9, "Zero-Hallucination Compliance", "Evidence-Grounded Structured Complaint Summarizer",
               "Why regulatory compliance mandates an extractive architecture rather than generative LLMs.")

    add_card(slide9, Inches(0.8), Inches(1.7), Inches(5.7), Inches(5.0))
    tb_l = slide9.shapes.add_textbox(Inches(1.1), Inches(1.9), Inches(5.1), Inches(4.5))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True

    p = tf_l.paragraphs[0]
    p.text = "The Zero-Hallucination Mandate"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = TEXT_MAIN

    p = tf_l.add_paragraph()
    p.text = "• Legal Risk of Generative LLMs: In legal dispute triage and regulatory compliance, generative models (like GPT/T5) risk hallucinating dates, monetary figures, or bank commitments that do not exist.\n" \
             "• Extractive Grounding: src/summarization/structured_summarizer.py enforces 100% source sentence grounding.\n" \
             "• Strict Verbatim Validator (validate_summary): Fails closed with an exception if any generated sentence contains text not found word-for-word in the consumer's narrative."
    p.font.size = Pt(11)
    p.font.color.rgb = TEXT_MUTED

    add_card(slide9, Inches(6.8), Inches(1.7), Inches(5.7), Inches(5.0))
    tb_r = slide9.shapes.add_textbox(Inches(7.1), Inches(1.9), Inches(5.1), Inches(4.5))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True

    p = tf_r.paragraphs[0]
    p.text = "Extracted Structured Schema"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = TEXT_MAIN

    p = tf_r.add_paragraph()
    p.text = "• Core Problem: Introductory sentence span defining the consumer's primary grievance.\n" \
             "• Consumer Concerns: Sentences identifying consumer harm, unverified debts, threats, or illegal charges.\n" \
             "• Timeline & Events: Chronological action sentences detected via date regex (DATE_RE) and interaction verbs (called, submitted, disputed).\n" \
             "• Requested Redress: Specific customer demands (refund, remove, discharge, correct, investigate).\n" \
             "• Provenance Mapping: Direct sentence index mapping ensuring traceability back to source."
    p.font.size = Pt(11)
    p.font.color.rgb = TEXT_MAIN

    # =========================================================================
    # SLIDE 10: Production Serving & System Architecture
    # =========================================================================
    slide10 = prs.slides.add_slide(blank_slide_layout)
    add_header(slide10, "System Architecture", "Production Inference Microservice & GPU Vector Index",
               "Real-time semantic retrieval and analysis running on Blackwell server infrastructure.")

    s_cards = [
        ("GPU VECTOR GALLERY", "32,019 Cases",
         "• 256-dimensional float32 vectors (32 MB)\n• Metadata index table (43 MB)\n• SHA-256: a9941be60d56...\n• Sub-10ms nearest neighbor search latency"),
        ("FASTAPI MICROSERVICE", "Live Microservice",
         "• Live on port 8000 (PID 3550266)\n• Endpoints: /retrieve, /summarize, /analyze, /health\n• Hardware: Blackwell MIG Slice 0\n• Full OpenAPI / Swagger documentation"),
        ("TESTING SANDBOX", "Apple Minimalist UI",
         "• Clean monochrome light theme\n• Preloaded test cases across all domains\n• Sub-second response rendering\n• Available at http://localhost:8080/demo.html")
    ]
    for i, (ttl, sub, details) in enumerate(s_cards):
        x = start_c + i * (c_w + c_gap)
        add_card(slide10, x, Inches(1.7), c_w, Inches(5.0))
        tb = slide10.shapes.add_textbox(x + Inches(0.2), Inches(1.9), c_w - Inches(0.4), Inches(4.5))
        tf = tb.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = ttl
        p1.font.size = Pt(9.5)
        p1.font.bold = True
        p1.font.color.rgb = TEXT_MUTED

        p2 = tf.add_paragraph()
        p2.text = sub
        p2.font.size = Pt(16)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_MAIN

        p3 = tf.add_paragraph()
        p3.text = details
        p3.font.size = Pt(10)
        p3.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 11: Final Delivery & Mentor Handover Checklist
    # =========================================================================
    slide11 = prs.slides.add_slide(blank_slide_layout)
    add_header(slide11, "Project Handover", "Final Delivery & Mentor Verification Sign-Off",
               "All components executed, audited, tested, and packaged for formal review.")

    add_card(slide11, Inches(0.8), Inches(1.7), Inches(11.733), Inches(5.0))
    tb_end = slide11.shapes.add_textbox(Inches(1.2), Inches(1.95), Inches(10.9), Inches(4.5))
    tf_end = tb_end.text_frame
    tf_end.word_wrap = True

    p = tf_end.paragraphs[0]
    p.text = "Delivery Audit Checklist (100% Complete)"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = ACCENT_GREEN

    checklist = [
        ("✔ Unit Test Suite:", "162 out of 162 unit tests passed (0 failures, 0 errors, 100% pass rate)."),
        ("✔ Model Promotion:", "Weakly supervised SupCon formally promoted after beating both frozen baseline (+34.86%) and TF-IDF (+15.43%)."),
        ("✔ Zero Data Leakage:", "Locked test split evaluated exactly once: 48.61% P@10 aligns within 0.36% of validation."),
        ("✔ Complete Documentation:", "Master final report, retrieval experiment report, data provenance, and taxonomy codebook packaged."),
        ("✔ Presentation PPTX:", "Widescreen executive PowerPoint presentation ready for mentor submission."),
        ("✔ Interactive Testing Sandbox:", "Running live at http://localhost:8080/demo.html with preloaded cases.")
    ]
    for tag, desc in checklist:
        p = tf_end.add_paragraph()
        p.text = f"{tag} {desc}"
        p.font.size = Pt(11)
        p.font.color.rgb = TEXT_MAIN

    # Save presentation
    prs.save(output_path)
    print(f"Successfully generated PowerPoint presentation at: {output_path}")

if __name__ == "__main__":
    out_dir = r"d:\NLP\final_deliverable"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "Cross_Domain_Complaint_Understanding_Final_Presentation.pptx")
    create_presentation(out_file)
