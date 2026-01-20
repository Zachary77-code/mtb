# Oncologist Treatment Plan

## Analysis Output

这是一个基于您提供的完整病历、病理及分子检测报告制定的深度治疗方案。

### 1. 执行摘要 (Executive Summary)

患者为70岁男性，IV期乙状结肠腺癌，伴双肺转移。疾病特点为**KRAS G12C突变**、**ATM胚系突变**及**超高TMB (79 mut/Mb)但微卫星稳定(MSS)**。既往多线治疗（含免疫联合）后进展，且有**药物性急性肾损伤(AKI)**病史（基线肌酐146 μmol/L，eGFR约40-50 mL/min）。

**核心策略**：
1.  **当前首选**：维持**氟泽雷赛 (KRAS G12Ci) + 西妥昔单抗**。这是目前针对KRAS G12C肠癌最强的循证方案，旨在克服单药耐药。
2.  **安全警示**：患者肾功能处于临界状态（CKD 3期），且正在服用CYP3A4底物药物（阿托伐他汀、硝苯地平）。需重点管理药物相互作用及肾毒性。
3.  **后线储备**：若当前方案进展，优先考虑**TAS-102 + 贝伐珠单抗**（需根据肾功能调整）或针对ATM突变的PARP抑制剂临床试验。

---

### 2. 治疗路线图 (Treatment Roadmap)

#### 方案 1：氟泽雷赛 (Fulzerasib) + 西妥昔单抗 (当前方案)
**证据等级**: B (基于同类药物Sotorasib/Adagrasib的III期数据及氟泽雷赛早期数据)
**治疗定位**: 跨线挽救治疗 (针对KRAS G12C阳性)

*   **科学依据**: 结直肠癌中单纯抑制KRAS G12C会导致EGFR反馈性激活，联合EGFR单抗（西妥昔单抗）可阻断此逃逸通路。CodeBreaK 300研究显示，类似组合（Sotorasib+Panitumumab）较标准治疗显著延长PFS。
*   **预期疗效**: 客观缓解率(ORR)约 30-40%，中位无进展生存期(mPFS) 5-6个月。
*   **给药方案**:
    *   **氟泽雷赛**: 600mg PO BID (参考II期推荐剂量，具体遵医嘱)。
    *   **西妥昔单抗**: 首剂 400 mg/m²，随后 250 mg/m² 每周一次 (或 500 mg/m² 每两周一次)。
*   **剂量调整 (肾功能)**:
    *   **氟泽雷赛**: 主要经肝代谢，eGFR >30 通常无需调整，但需密切监测。
    *   **西妥昔单抗**: 无需根据肾功能调整剂量。
*   **关键毒性管理**:
    *   **皮肤毒性**: 痤疮样皮疹（西妥昔单抗常见），建议预防性使用多西环素或外用激素。
    *   **低镁血症**: 西妥昔单抗可导致肾性镁丢失，需每次输注前监测血镁。

#### 方案 2：TAS-102 (曲氟尿苷替匹嘧啶) + 贝伐珠单抗 (后线标准)
**证据等级**: A (NCCN 1类推荐，SUNLIGHT研究)
**治疗定位**: 标准三线/四线治疗

*   **科学依据**: SUNLIGHT研究证实，TAS-102联合贝伐珠单抗相比TAS-102单药，显著延长总生存期（10.8 vs 7.5个月）。
*   **给药方案**:
    *   **TAS-102**: 35 mg/m² PO BID，d1-5, d8-12，每28天一周期。
    *   **贝伐珠单抗**: 5 mg/kg IV，每2周一次。
*   **肾功能特别警示**:
    *   FDA说明书指出：轻中度肾受损（CrCl 30-89 mL/min）**无需调整起始剂量**。
    *   但鉴于患者既往有AKI史，建议密切监测骨髓抑制（肾功能差者发生率更高）。若CrCl跌至30以下，需减量至20 mg/m²。

#### 方案 3：临床试验 (优先考虑)
**证据等级**: C (探索性)
*   **方向 A (耐药克服)**: **Glecirasib (KRAS G12Ci) + SHP2抑制剂** (NCT05288205)。SHP2是KRAS耐药的关键旁路，联合抑制可能逆转耐药。
*   **方向 B (新机制)**: **TROP2 ADC (Dato-DXd)**。利用细胞毒药物定向递送，避开RAS信号通路。
*   **方向 C (ATM靶向)**: **PARP抑制剂** (如奥拉帕利)。基于ATM胚系突变导致的同源重组修复缺陷(HRD)。

---

### 3. 药物相互作用警示 (Drug-Drug Interactions)

患者合并用药较多，且KRAS抑制剂通常是**CYP3A4诱导剂**，可能导致合并用药失效。

| 合并药物 | 相互作用风险 | 建议 |
| :--- | :--- | :--- |
| **硝苯地平** (降压) | **高风险**。KRAS抑制剂可能诱导CYP3A4，加速硝苯地平代谢，导致**血压控制不佳**。 | 密切监测血压。若血压升高，建议更换为非CYP3A4依赖的降压药（如ACEI/ARB类：缬沙坦、贝那普利）。 |
| **阿托伐他汀** (降脂) | **中风险**。代谢加速，降脂效果降低。 | 监测血脂。必要时增加剂量或更换为瑞舒伐他汀（受CYP3A4影响较小）。 |
| **达格列净** (降糖) | 低风险。主要经UGT代谢。 | 继续使用，注意监测尿路感染（SGLT2i副作用）。 |
| **西妥昔单抗** | 与上述口服药无代谢相互作用。 | 安全。 |

---

### 4. 器官功能与剂量调整 (Organ Function & Safety)

#### 肾功能 (当前主要瓶颈)
*   **现状**: 肌酐 146 μmol/L，eGFR ~40-50 mL/min (CKD 3a期)。
*   **既往史**: 呋喹替尼致急性肾损伤。
*   **决策规则**:
    *   ❌ **绝对禁忌**: 顺铂、高剂量甲氨蝶呤、NSAIDs（布洛芬等止痛药）。
    *   ⚠️ **慎用/减量**: 奥沙利铂（若再挑战需减量）、TAS-102（密切监测）、唑来膦酸（若有骨转移，需根据肌酐调整或换用地舒单抗）。
    *   ✓ **安全**: 西妥昔单抗、贝伐珠单抗（需监测蛋白尿）、氟泽雷赛（主要肝代谢）。

#### 肝功能
*   **现状**: 既往肝转移切除，目前无明显异常描述。
*   **策略**: 氟泽雷赛有潜在肝毒性，需每2周查肝功能。若ALT/AST > 3x ULN，需暂停用药。

#### 血液学
*   **现状**: 既往有II度血小板减少。
*   **策略**: TAS-102易致骨髓抑制，若血小板 <75×10⁹/L，需推迟化疗。

---

### 5. 不建议的方案 (Not Recommended)

1.  **呋喹替尼 (Fruquintinib)**:
    *   **原因**: 既往导致严重急性肾损伤（AKI），属于**绝对禁忌**。
    *   **替代**: 贝伐珠单抗（大分子抗血管药，肾毒性相对较小，主要风险是蛋白尿和高血压）。

2.  **免疫检查点抑制剂单药 (PD-1/PD-L1)**:
    *   **原因**: 尽管TMB高，但患者为MSS表型，且既往信迪利单抗联合治疗已进展。单纯免疫治疗有效率极低。
    *   **例外**: 仅在临床试验中考虑新型免疫组合（如联合LAG-3或TIGIT）。

3.  **伊立替康 (Irinotecan)**:
    *   **原因**: 既往二线治疗效果一般(SD)，且患者高龄、体弱，易发生迟发性腹泻，加重脱水和肾损伤风险。

---

### 6. 监测与随访计划

*   **疗效评估**: 每6-8周行胸腹盆CT。重点关注双肺转移灶变化。
*   **液体活检 (ctDNA)**:
    *   **时机**: 每次影像学评估进展时。
    *   **目的**: 监测KRAS G12C耐药突变（如Y96D）、MET扩增或BRAF突变。这直接决定下一线是否能换用其他靶向药。
*   **实验室检查**:
    *   **血常规/肝肾功能**: 每2周一次（前3个月），之后每月一次。
    *   **电解质 (镁/钙/钾)**: 每次输注西妥昔单抗前必查（防低镁血症诱发心律失常）。
    *   **尿常规**: 每月一次（监测贝伐珠单抗可能引起的蛋白尿）。

### 7. 总结
患者目前处于精准靶向治疗的关键窗口期。**氟泽雷赛+西妥昔单抗**是基于分子机制的最佳选择。治疗成功的关键在于**“护肾”**——避免肾毒性药物叠加，并因KRAS抑制剂的酶诱导作用调整降压药，防止高血压进一步损害肾脏。

---

## Tool Call Details

### Tool Call 1: `search_nccn`
**Timestamp:** 2026-01-20 15:15:21

**Parameters:**
```json
{
  "cancer_type": "Colon Cancer"
}
```

**Result:**
```
**NCCN 指南检索结果**
**查询**: Colon Cancer
**找到 5 条相关内容**:
---
### 1. （2025.V1）NCCN临床实践指南：结肠癌 (245/1162)
**癌症类型**: Colon Cancer
**相关度**: 61.55%

[Page 62]
NCCN Guidelines Version 1.2025
Colon Cancer
Version 1.2025, 02/07/25 © 2025 National Comprehensive Cancer Network® (NCCN®), All rights reserved. NCCN Guidelines® and this illustration may not be reproduced in any form without the express written permission of NCCN. Note: All recommendations are category 2A unless otherwise indicated. NCCN Guidelines Index
Table of Contents
Discussion
PRINCIPLES OF APPENDICEAL ADENOCARCINOMA
COL-I
2 OF 3
Localized Disease
• Screening colonoscopy is recommended in all patients diagnosed
with AA prior to definitive resection to rule out synchronous large
polyps or cancers. • Right hemicolectomy with adequate lymphadenectomy is
recommended.

---
### 2. （2025.V1）NCCN临床实践指南：结肠癌 (757/1162)
**癌症类型**: Colon Cancer
**相关度**: 59.93%

[Page 156]
Version 1.2025 © 2025 National Comprehensive Cancer Network© (NCCN©), All rights reserved. NCCN Guidelines® and this illustration may not be reproduced in any form without the express written permission of NCCN. NCCN Guidelines Version 1.2025 
Colon Cancer 
MS-89 
as treatment recommendations can vary considerably at all stages of 
colon cancer based on these biomarker results. The recommended surgical procedure for resectable colon cancer is an en 
bloc resection and adequate lymphadenectomy. Adequate pathologic 
assessment of the resected lymph nodes is important with a goal of 
evaluating at least 12 nodes. Adjuvant chemotherapy is recommended for 
patients with stage III disease and is also an option for some patients with 
high-risk stage II disease. The preferred regimens 
... (共 944 字符)

---
### 3. （2025.V1）NCCN临床实践指南：结肠癌 (21/1162)
**癌症类型**: Colon Cancer
**相关度**: 58.21%

COL-B 6 of 10
• POLE/POLD1
Bullet 4 revised: NGS of CRCs arising in patients with either germline or somatic ED PVs demonstrate an ultramutator ultra-hypermutated phenotype
identified as extremely high tumor mutational burden (TMB>50 mut/Mb >100 mut/Mb). COL-C 1 of 6
• Principles of Surgery and Locoregional Therapies
Colectomy
◊Bullet 2, sub-bullet 2 revised: Consider Preoperative localization is performed (eg, radiographic identification, preoperative endoscopic marking,
endoscopic landmarks) of lesion(s). ◊Bullet 2, sub-bullet 4 revised: Minimally invasive approaches are generally not indicated for locally advanced cancer (eg, invasion into adjacent
structure) or acute bowel obstruction.... Updates in Version 1.2025 of the NCCN Guidelines for Colon Cancer from Version 6.2024 include: 

... (共 895 字符)

---
### 4. （2025.V1）NCCN临床实践指南：结肠癌 (249/1162)
**癌症类型**: Colon Cancer
**相关度**: 57.66%

If a patient is not a candidate for surgery, treatment should follow 
metastatic colon cancer guidelines. The extent of cytoreduction should be individualized. Surgery is 
discouraged for high PCI, biliary obstruction, extensive disease at 
the gastrohepatic ligament/porta hepatis, extensive retroperitoneal 
disease, intraparenchymal liver lesions requiring a major 
resection, diffuse small bowel serosa/mesenteric involvement, and/
or multiple sites of small bowel obstruction. References on COL-I (3 of 3)
Systemic Therapy (COL-D)
NCCN 授权医脉通提供NCCN指南全文下载。6261163于2025/02/18,11:03在医脉通平台下载，仅供个人使用，严禁分发。2025 美国国家综合癌症网络版权所有。

---
### 5. （2025.V1）NCCN临床实践指南：结肠癌 (336/1162)
**癌症类型**: Colon Cancer
**相关度**: 57.36%

[Page 81]
Version 1.2025 © 2025 National Comprehensive Cancer Network© (NCCN©), All rights reserved. NCCN Guidelines® and this illustration may not be reproduced in any form without the express written permission of NCCN. NCCN Guidelines Version 1.2025 
Colon Cancer 
MS-14 
However, in addition to the option of observation, the Panel includes the 
option of colectomy in patients with a completely removed, single-
specimen, sessile polyp with favorable histologic features and clear 
margins. This option is included because the literature seems to indicate 
that patients with sessile polyps may have a significantly greater incidence 
of adverse outcomes, including disease recurrence, mortality, and 
hematogenous metastasis compared with those with pedunculated polyps.

---

**注意**: 以上内容来自 NCCN 指南 PDF，具体治疗方案请结合最新版指南和患者具体情况。

```

### Tool Call 2: `search_fda_labels`
**Timestamp:** 2026-01-20 15:15:22

**Parameters:**
```json
{
  "drug_name": "trifluridine and tipiracil"
}
```

**Result:**
```
**FDA 药品说明书**

**药物**: TRIFLURIDINE AND TIPIRACIL
**商品名**: LONSURF
**生产商**: Taiho Pharmaceutical Co., Ltd.

### 适应症
1 INDICATIONS AND USAGE LONSURF is a combination of trifluridine, a nucleoside metabolic inhibitor, and tipiracil, a thymidine phosphorylase inhibitor, indicated for the treatment of adult patients with: metastatic colorectal cancer as a single agent or in combination with bevacizumab who have been previously treated with fluoropyrimidine-, oxaliplatin- and irinotecan-based chemotherapy, an anti-VEGF biological therapy, and if RAS wild-type, an anti-EGFR therapy. ( 1.1 ) metastatic gastric or gastroesophageal junction adenocarcinoma previously treated with at least two prior lines of chemotherapy that included a fluoropyrimidine, a platinum, either a taxane or irinotecan, and if appropriate, HER2/neu-targeted therapy. ( 1.2 ) 1.1 Metastatic Colorectal Cancer LONSURF, as a single agent or in combination with bevacizumab, is indicated for the treatment of adult patients with metastatic colorectal cancer previously treated with fluoropyrimidine-, oxaliplatin- and irinotecan-based chemotherapy, an anti-VEGF biological therapy, and if RAS wild-type, an anti-EGFR therapy. 1.2 Metastatic Gastric Cancer LONSURF is indicated for the treatment of adult patients with metastatic gastric or gastroesophageal junction adenocarcinoma previously treated with at least two prior lines of chemotherapy that included a fluoropyrimidine, a platinum, either a taxane or irinotecan, and if appropriate, HER2/neu-targeted therapy.

### 剂量与用法
2 DOSAGE AND ADMINISTRATION Recommended Dosage : 35 mg/m 2 /dose orally twice daily with food on Days 1 through 5 and Days 8 through 12 of each 28-day cycle. ( 2.1 ) 2.1 Recommended Dosage The recommended dosage of LONSURF as a single agent or in combination with bevacizumab is 35 mg/m 2 up to a maximum of 80 mg per dose (based on the trifluridine component) orally twice daily with food on Days 1 through 5 and Days 8 through 12 of each 28-day cycle until disease progression or unacceptable toxicity. Round dose to the nearest 5 mg increment. Refer to the Prescribing Information for bevacizumab dosing information. Instruct patients to swallow LONSURF tablets whole. Instruct patients not to retake doses of LONSURF that are vomited or missed and to continue with the next scheduled dose. LONSURF is a cytotoxic drug. Follow applicable special handling and disposal procedures. 1 Table 1 shows the calculated initial daily dose based on body surface area (BSA). Table 1: Recommended Dosage According to Body Surface Area (BSA) BSA (m2) Total daily dose (mg) Dose (mg) administered twice daily Tablets per dose 15 mg 20 mg < 1.07 70 35 1 1 1.07 – 1.22 80 40 0 2 1.23 – 1.37 90 45 3 0 1.38 – 1.52 100 50 2 1 1.53 – 1.68 110 55 1 2 1.69 – 1.83 120 60 0 3 1.84 – 1.98 130 65 3 1 1.99 – 2.14 140 70 2 2 2.15 – 2.29 150 75 1 3 ≥2.30 160 80 0 4 2.2 Dosage Modifications for Adverse Reactions Obtain complete blood cell counts prior to and on Day 15 of each cycle [see Warnings and Precautions (5.1) ] . Do not initiate the cycle of LONSURF until: Absolute neutrophil count (ANC) greater than or equal to 1,500/mm 3 or febrile neutropenia is resolved Platelets greater than or equal to 75,000/mm 3 Grade 3 or 4 non-hematological adverse reactions are resolved to Grade 0 or 1 Within a treatment cycle, withhold LONSURF for any of the following: Absolute neutrophil count (ANC) less than 500/mm 3 or febrile neutropenia Platelets less than 50,000/mm 3 Grade 3 or 4 non-hematologic adverse reaction After 

### 警告与注意事项
5 WARNINGS AND PRECAUTIONS Severe Myelosuppression: Obtain complete blood counts prior to and on Day 15 of each cycle. Withhold and resume at next lower LONSURF dosage as recommended. ( 2.1 , 5.1 ) Embryo-Fetal Toxicity: Can cause fetal harm. Advise females of reproductive potential of the potential risk to a fetus and to use effective contraception. ( 5.2 , 8.1 , 8.3 ) 5.1 Severe Myelosuppression In the 1114 patients who received LONSURF as a single agent, LONSURF caused severe or life-threatening myelosuppression (Grade 3-4) consisting of neutropenia (38%), anemia (17%), thrombocytopenia (4%) and febrile neutropenia (3%). Three patients (0.3%) died due to neutropenic infection/sepsis; four other patients (0.5%) died due to septic shock. A total of 14% of patients received granulocyte-colony stimulating factors. In the 246 patients who received LONSURF in combination with bevacizumab, LONSURF caused severe or life-threatening myelosuppression (Grade 3-4) consisting of neutropenia (52%), anemia (5%), thrombocytopenia (4%) and febrile neutropenia (0.4%). One patient (0.4%) died due to abdominal sepsis and two other patients (0.8%) died due to septic shock. A total of 29% of patients received granulocyte-colony stimulating factors. Obtain complete blood counts prior to and on Day 15 of each cycle of LONSURF and more frequently as clinically indicated. Withhold LONSURF for severe myelosuppression and resume at the next lower dosage [see Dosage and Administration (2.2) ] . 5.2 Embryo-Fetal Toxicity Based on animal studies and its mechanism of action, LONSURF can cause fetal harm when administered to a pregnant woman. Trifluridine/tipiracil caused embryo-fetal lethality and embryo-fetal toxicity in pregnant rats when orally administered during gestation at dosage levels resulting in exposures lower than those achieved at the recommended dosage of 35 mg/m 2 twice daily. Advise pregnant women of the potential risk to the fetus. Advise females of reproductive potential to u

### 禁忌症
4 CONTRAINDICATIONS None. None. ( 4 )

### 不良反应
6 ADVERSE REACTIONS The following clinically significant adverse reactions are described elsewhere in the labeling: Severe Myelosuppression [see Warnings and Precautions (5.1) ] The most common adverse reactions or laboratory abnormalities for single agent LONSURF (≥10%) are neutropenia, anemia, thrombocytopenia, fatigue, nausea, decreased appetite, diarrhea, vomiting, abdominal pain, and pyrexia. ( 6.1 ) The most common adverse reactions or laboratory abnormalities for LONSURF in combination with bevacizumab (≥20%) are neutropenia, anemia, thrombocytopenia, fatigue, nausea, increased AST, increased ALT, increased alkaline phosphatase, decreased sodium, diarrhea, abdominal pain, and decreased appetite. ( 6.1 ) To report SUSPECTED ADVERSE REACTIONS, contact Taiho Oncology, Inc. at 1-844-878-2446 or FDA at 1-800-FDA-1088 or www.fda.gov/medwatch . 6.1 Clinical Trials Experience Because clinical trials are conducted under widely varying conditions, adverse reaction rates observed in the clinical trials of a drug cannot be directly compared to rates in the clinical trials of another drug and may not reflect the rates observed in practice. The data described in the WARNINGS AND PRECAUTIONS section and below reflect exposure to LONSURF at the recommended dose in 533 patients with metastatic colorectal cancer in RECOURSE, 246 patients with metastatic colorectal cancer treated with LONSURF as monotherapy in SUNLIGHT and 335 patients with metastatic gastric cancer in TAGS. Among the 1114 patients who received LONSURF as a single agent, 12% were exposed for 6 months or longer and 1% were exposed for 12 months or longer. The most common adverse reactions or laboratory abnormalities (≥10%) were neutropenia, anemia, thrombocytopenia, fatigue, nausea, decreased appetite, diarrhea, vomiting, abdominal pain, and pyrexia. Among the 246 patients with metastatic colorectal cancer treated with LONSURF in combination with bevacizumab in SUNLIGHT, 39% were exposed for 6 months or longer, 

**参考**: https://labels.fda.gov (搜索 TRIFLURIDINE AND TIPIRACIL)
```

### Tool Call 3: `search_fda_labels`
**Timestamp:** 2026-01-20 15:15:23

**Parameters:**
```json
{
  "drug_name": "cetuximab"
}
```

**Result:**
```
**FDA 药品说明书**

**药物**: CETUXIMAB
**商品名**: ERBITUX
**生产商**: ImClone LLC

### 适应症
1 INDICATIONS AND USAGE ERBITUX ® is an epidermal growth factor receptor (EGFR) antagonist indicated for treatment of: Head and Neck Cancer Locally or regionally advanced squamous cell carcinoma of the head and neck in combination with radiation therapy. ( 1.1 , 14.1 ) Recurrent locoregional disease or metastatic squamous cell carcinoma of the head and neck in combination with platinum-based therapy with fluorouracil. ( 1.1 , 14.1 ) Recurrent or metastatic squamous cell carcinoma of the head and neck progressing after platinum-based therapy. ( 1.1 , 14.1 ) Colorectal Cancer K-Ras wild-type, EGFR-expressing, metastatic colorectal cancer as determined by an FDA-approved test in combination with FOLFIRI for first-line treatment, in combination with irinotecan in patients who are refractory to irinotecan-based chemotherapy, as a single-agent in patients who have failed oxaliplatin- and irinotecan-based chemotherapy or who are intolerant to irinotecan. ( 1.2 , 5.7 , 12.1 , 14.2 ) Limitations of Use: ERBITUX is not indicated for treatment of Ras-mutant colorectal cancer or when the results of the Ras mutation tests are unknown. ( 5.7 ) BRAF V600E Mutation-Positive Metastatic Colorectal Cancer (CRC) in combination with encorafenib, for the treatment of adult patients with metastatic colorectal cancer (CRC) with a BRAF V600E mutation, as detected by an FDA-approved test, after prior therapy. ( 1.3 ) 1.1 Squamous Cell Carcinoma of the Head and Neck (SCCHN) ERBITUX ® is indicated: in combination with radiation therapy for the initial treatment of locally or regionally advanced squamous cell carcinoma of the head and neck (SCCHN). in combination with platinum-based therapy with fluorouracil for the first-line treatment of patients with recurrent locoregional disease or metastatic SCCHN. as a single-agent for the treatment of patients with recurrent or metastatic SCCHN for whom prior platinum-based therapy has failed. 1.2 K-Ras Wild-type, EGFR-expressing Colorectal Cancer (CRC)

### 剂量与用法
2 DOSAGE AND ADMINISTRATION Premedicate with an H 1 receptor antagonist. ( 2.4 ) In Combination With Radiation Therapy: Initial dose: 400 mg/m 2 administered as a 120-minute intravenous infusion one week prior to initiating a course of radiation therapy. ( 2.2 ) Subsequent doses: 250 mg/m 2 administered as a 60-minute infusion every week for the duration of radiation therapy (6–7 weeks). ( 2.2 ) Complete ERBITUX administration 1 hour prior to radiation therapy. ( 2.2 ) As Single-Agent or in Combination With Chemotherapy: Weekly: Administer initial dose of 400 mg/m 2 as a 120-minute intravenous infusion, and subsequent doses of 250 mg/m 2 infused over 60 minutes once weekly. ( 2.2 , 2.3 ) Biweekly: Administer 500 mg/m 2 as a 120-minute intravenous infusion every two weeks. ( 2.2 , 2.3 ) Complete ERBITUX administration 1 hour prior to chemotherapy. Continue treatment until disease progression or unacceptable toxicity. ( 2.2 , 2.3 ) See full prescribing information for dosage adjustments for adverse reactions. ( 2.5 ) 2.1 Patient Selection Select patients with metastatic colorectal cancer (CRC) for treatment with ERBITUX based on the presence of: Ras wild-type, EGFR-expressing CRC [see Clinical Studies ( 14.2 )], or BRAF V600E mutation-positive metastatic CRC [see Clinical Studies ( 14.3 )] Information on FDA-approved tests for the detection of K-Ras or BRAF V600E mutations in CRC in patients with metastatic CRC is available at: http://www.fda.gov/CompanionDiagnostics. 2.2 Recommended Dosage for Squamous Cell Carcinoma of the Head and Neck (SCCHN) In combination with radiation therapy Initial dose: 400 mg/m 2 administered as a 120-minute intravenous infusion one week prior to initiating a course of radiation therapy. Subsequent doses: 250 mg/m 2 administered as a 60-minute infusion every week for the duration of radiation therapy (6–7 weeks). Complete ERBITUX administration 1 hour prior to radiation therapy. As a single-agent or in combination with platinum-based thera

### ⚠️ 黑框警告
WARNING: INFUSION REACTIONS and CARDIOPULMONARY ARREST Infusion Reactions: ERBITUX can cause serious and fatal infusion reactions [see Warnings and Precautions ( 5.1 ), Adverse Reactions ( 6 )] . Immediately interrupt and permanently discontinue ERBITUX for serious infusion reactions [see Dosage and Administration ( 2.5 )] . Cardiopulmonary Arrest: Cardiopulmonary arrest or sudden death occurred in patients with squamous cell carcinoma of the head and neck receiving ERBITUX with radiation therapy or a cetuximab product with platinum-based therapy and fluorouracil. Monitor serum electrolytes, including serum magnesium, potassium, and calcium, during and after ERBITUX administration [see Warnings and Precautions ( 5.2 , 5.6 )] . WARNING: INFUSION REACTIONS and CARDIOPULMONARY ARREST See full prescribing information for complete boxed warning. ERBITUX can cause serious and fatal infusion reactions. ( 5.1 , 6 ) Immediately interrupt and permanently discontinue ERBITUX for serious infusion reactions. ( 2.5 ) Cardiopulmonary arrest or sudden death occurred in patients with squamous cell carcinoma of the head and neck receiving ERBITUX with radiation therapy or with a cetuximab product with platinum-based therapy and fluorouracil. Monitor serum electrolytes, including serum magnesium, potassium, and calcium, during and after ERBITUX administration. ( 5.2 , 5.6 )

### 警告与注意事项
5 WARNINGS AND PRECAUTIONS Infusion Reactions: Monitor patients following infusion. Immediately stop and permanently discontinue ERBITUX for serious infusion reactions. ( 2.5 , 5.1 ) Cardiopulmonary Arrest: Monitor serum electrolytes during and after ERBITUX. ( 5.2 , 5.6 ) Pulmonary Toxicity: Interrupt or permanently discontinue for acute onset or worsening of pulmonary symptoms. ( 2.5 , 5.3 ) Dermatologic Toxicity: Monitor for dermatologic toxicities or infectious sequelae. Limit sun exposure. ( 2.5 , 5.4 ) Hypomagnesemia and Accompanying Electrolyte Abnormalities: Monitor during treatment and for at least 8 weeks following the completion. Replete electrolytes as necessary. ( 5.6 ) Increased tumor progression, increased mortality, or lack of benefit observed in patients with Ras-mutant mCRC. ( 5.7 ) Embryo-Fetal Toxicity: Can cause fetal harm. Advise females of potential risk to the fetus and to use effective contraception. ( 5.8 , 8.1 , 8.3 ) 5.1 Infusion Reactions ERBITUX can cause serious and fatal infusion reactions. Infusion reactions of any grade occurred in 8.4% of 1373 patients who received ERBITUX across clinical trials. Severe (Grades 3 and 4) infusion reactions occurred in 2.2% of patients [see Adverse Reactions ( 6.1 )] . Signs and symptoms included rapid onset of airway obstruction (bronchospasm, stridor, hoarseness), hypotension, shock, loss of consciousness, myocardial infarction, and/or cardiac arrest. The risk of anaphylactic reactions may be increased in patients with a history of tick bites, red meat allergy, or in the presence of IgE antibodies directed against galactose-α-1,3-galactose (alpha-gal). Consider testing patients for alpha-gal IgE antibodies using FDA-cleared methods prior to initiating ERBITUX. Negative results for alpha-gal antibodies do not rule out the risk of severe infusion reactions. Approximately 90% of severe infusion reactions occurred with the first infusion despite premedication with antihistamines. Infusion reactions may

### 禁忌症
4 CONTRAINDICATIONS None. None. ( 4 )

### 不良反应
6 ADVERSE REACTIONS The following adverse reactions are discussed in greater detail in other sections of the label: Infusion reactions [see Warnings and Precautions ( 5.1 )] . Cardiopulmonary arrest [see Warnings and Precautions ( 5.2 )] . Pulmonary toxicity [see Warnings and Precautions ( 5.3 )] . Dermatologic toxicity [see Warnings and Precautions ( 5.4 )] . Hypomagnesemia and Electrolyte Abnormalities [see Warnings and Precautions ( 5.6 )] . The most common adverse reactions (incidence ≥25%) with Erbitux as a single-agent or in combination with radiotherapy or chemotherapy (FOLFIRI, Irinotecan and 5-Fluorouracil/Platinum) are: cutaneous adverse reactions (including rash, pruritus, and nail changes), headache, diarrhea, and infection. ( 6 ) The most common adverse reactions (>25%) for ERBITUX, in combination with encorafenib, are fatigue, nausea, diarrhea, dermatitis acneiform, abdominal pain, decreased appetite, arthralgia, and rash. ( 6 ). To report SUSPECTED ADVERSE REACTIONS, contact Eli Lilly and Company at 1-800-LillyRx (1-800-545-5979) or FDA at 1-800-FDA-1088 or www.fda.gov/medwatch. 6.1 Clinical Trials Experience Because clinical trials are conducted under widely varying conditions, adverse reaction rates observed in the clinical trials of a drug cannot be directly compared to rates in the clinical trials of another drug and may not reflect the rates observed in practice. The data described in Warnings and Precautions reflect exposure to ERBITUX in 1373 patients with SCCHN or CRC enrolled in clinical trials and treated at the recommended dosage for a median of 7 to 14 weeks [see Clinical Studies ( 14.1 , 14.2 )] . The most common adverse reactions in clinical trials with ERBITUX as a single-agent or in combination with radiotherapy or chemotherapy [FOLFIRI, irinotecan and 5-fluorouracil/platinum] (incidence ≥25%) include cutaneous adverse reactions (including rash, pruritus, and nail changes), headache, diarrhea, and infection. Squamous Cell Carcinoma of 

**参考**: https://labels.fda.gov (搜索 CETUXIMAB)
```

### Tool Call 4: `search_rxnorm`
**Timestamp:** 2026-01-20 15:15:29

**Parameters:**
```json
{
  "check_interactions": [
    "atorvastatin",
    "nifedipine",
    "dapagliflozin"
  ],
  "drug_name": "sotorasib"
}
```

**Result:**
```
**RxNorm 药物查询结果**

**药物**: sotorasib
**RxCUI**: 2550714

### 药物相互作用 (FDA 说明书)

*注: RxNorm 无数据，以下信息来自 FDA 药品说明书*

7 DRUG INTERACTIONS Acid-Reducing Agents: Avoid coadministration with proton pump inhibitors (PPIs) and H 2 receptor antagonists. If an acid-reducing agent cannot be avoided, administer LUMAKRAS 4 hours before or 10 hours after a local antacid. ( 2.4 , 7.1 ) Strong CYP3A4 Inducers: Avoid coadministration with strong CYP3A4 inducers. ( 7.1 ) CYP3A4 Substrates: Avoid coadministration with CYP3A4 substrates for which minimal concentration changes may lead to therapeutic failures of the substrate. If coadministration cannot be avoided, adjust the substrate dosage in accordance to its Prescribing Information. ( 7.2 ) P-gp substrates: Avoid coadministration with P-gp substrates for which minimal concentration changes may lead to serious toxicities. If coadministration cannot be avoided, decrease the substrate dosage in accordance to its Prescribing Information. ( 7.2 ) 7.1 Effects of Other Drugs on LUMAKRAS Acid-Reducing Agents The solubility of sotorasib is pH-dependent. Coadministration of LUMAKRAS with gastric acid-reducing agents decreased sotorasib concentrations [see Clinical Pharmacology (12.3) ] , which may reduce the efficacy of sotorasib. Avoid coadministration of LUMAKRAS with proton pump inhibitors (PPIs), H 2 receptor antagonists, and locally acting antacids. If coadministration with an acid-reducing agent cannot be avoided, administer LUMAKRAS 4 hours before or 10 hours after administration of a locally acting antacid [see Dosage and Administration (2.4) ] . Strong CYP3A4 Inducers Sotorasib is a CYP3A4 substrate. Coadministration of LUMAKRAS with a strong CYP3A4 inducer decreased sotorasib concentrations [see Clinical Pharmacology (12.3) ] , which may reduce the efficacy of sotorasib. Avoid coadministration of LUMAKRAS with strong CYP3A4 inducers . 7.2 Effects of LUMAKRAS on Other Drugs CYP3A4 Substrates Sotorasib is a CYP3A4 inducer. Coadministration of LUMAKRAS with a CYP3A4 substrate decreased its plasma concentrations [see Clinical Pharmacology (12.3) ] 

**参考**: https://rxnav.nlm.nih.gov
```
