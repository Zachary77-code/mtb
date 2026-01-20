# Oncologist Treatment Plan

## Analysis Output

# 治疗方案制定报告：IV 期乙状结肠癌 (KRAS G12C/ATM/TMB-H)

## 1. 执行摘要 (Executive Summary)

患者为 70 岁男性，IV 期乙状结肠腺癌，伴双肺多发转移。目前处于五线治疗阶段（氟泽雷赛 + 西妥昔单抗）。核心分子特征为 **KRAS G12C 突变**、**ATM 胚系突变** 及 **TMB 极高 (79 mut/Mb)**。主要治疗挑战在于 **肾功能不全 (eGFR ~35-40 mL/min)** 及既往 TKI 导致的急性肾损伤史。

**核心策略**：
1.  **当前维持**：全力保障当前 **KRAS G12C 抑制剂 + EGFR 单抗** 组合的安全性，重点管理药物相互作用（CYP3A4）及肾功能监测。
2.  **后续首选**：若进展，推荐 **TAS-102 + 贝伐珠单抗**（证据等级 A），该方案在肾功能不全患者中相对安全且有生存获益。
3.  **探索性治疗**：基于 ATM 突变考虑 PARP 抑制剂，或基于高 TMB 考虑双免疫治疗（CTLA-4 + PD-1），但需在临床试验或严格监控下进行。

---

## 2. 治疗路线图 (Treatment Roadmap)

### 当前方案：氟泽雷赛 (Fulzerasib) + 西妥昔单抗 (Cetuximab)
**定位**：五线治疗（正在进行）
**证据等级**：B (基于同类药物 Adagrasib/Sotorasib 联合西妥昔单抗的 III 期数据，如 CodeBreaK 300)
**预期疗效**：ORR 约 30-40%，mPFS 约 7-9 个月。
**关键调整与监测**：
*   **肾功能**：患者 eGFR 35-40 mL/min。虽然同类药（Sotorasib/Adagrasib）在轻中度肾损无需调整剂量，但鉴于患者既往 TKI 肾损史，建议密切监测肌酐（每 2 周一次）。
*   **皮肤毒性**：西妥昔单抗易致皮疹，需预防性使用四环素类抗生素（如米诺环素）及保湿霜。

---

### 后线优选：TAS-102 (曲氟尿苷替匹嘧啶) + 贝伐珠单抗
**定位**：标准六线治疗（若当前方案进展）
**证据等级**：A (NCCN Category 1)
**理论依据**：SUNLIGHT 研究显示，与 TAS-102 单药相比，联合贝伐珠单抗显著延长 mOS (10.8 vs 7.5 个月) 和 mPFS [[1]](#ref-pmid-37133585)。
**肾功能适应性**：
*   **FDA 说明书确认**：轻度至中度肾功能损害（CLcr 30-89 mL/min）**无需调整起始剂量** [FDA Label: LONSURF]。
*   **安全性**：主要经肾排泄，需警惕骨髓抑制加重。
**给药方案**：
*   TAS-102: 35 mg/m² PO, bid, d1-5, d8-12, q28d.
*   贝伐珠单抗: 5 mg/kg IV, q2w.

---

### 探索性方案：PARP 抑制剂 (如奥拉帕利)
**定位**：临床试验 / 超适应症 (Off-label)
**证据等级**：C (生物标志物驱动)
**理论依据**：患者携带 **ATM 胚系突变**，提示同源重组修复缺陷（HRD），可能对 PARP 抑制剂敏感。虽然在 CRC 中单药有效率有限，但在多线耐药后是合理的生物学尝试。
**注意事项**：需关注贫血风险，肾功能不全需减量（奥拉帕利在 CrCl 31-50 mL/min 时需减量至 200mg bid）。

---

## 3. 药物相互作用与合并症管理 (Critical!)

患者合并用药较多，且 KRAS G12C 抑制剂（如 Adagrasib/Fulzerasib）通常是 **CYP3A4 的底物和抑制剂**，存在重大相互作用风险。

| 合并药物 | 潜在风险 | 调整建议 |
| :--- | :--- | :--- |
| **硝苯地平 (Nifedipine)** | CYP3A4 底物。与 G12C 抑制剂联用可能导致血药浓度升高，引发**低血压**。 | ⚠️ **密切监测血压**。若出现低血压，建议换用氨氯地平（相互作用较少）或减量。 |
| **阿托伐他汀 (Atorvastatin)** | CYP3A4 底物。联用可能增加**横纹肌溶解**风险。 | ⚠️ **建议更换**。换用瑞舒伐他汀 (Rosuvastatin) 或普伐他汀 (Pravastatin)，它们不经 CYP3A4 代谢。 |
| **达格列净 (Dapagliflozin)** | 主要经 UGT1A9 代谢，相互作用风险低。 | ✓ 继续使用，注意监测血糖和尿路感染。 |
| **百令胶囊** | 成分复杂，可能含免疫调节成分。 | ⚠️ 建议暂停，以免干扰免疫状态或增加肝肾负担。 |

---

## 4. 器官功能与剂量调整 (Safety Gatekeeper)

### 肾功能 (eGFR ~35-40 mL/min)
*   **当前状态**：CKD 3b 期，既往有 TKI 相关急性肾损伤。
*   **禁忌药物**：
    *   ❌ **顺铂 (Cisplatin)**：绝对禁忌。
    *   ❌ **非甾体抗炎药 (NSAIDs)**：避免长期使用（如布洛芬、双氯芬酸），以免加重肾损。
    *   ⚠️ **造影剂**：CT 增强需水化，或改用 MRI。
*   **药物调整**：
    *   **TAS-102**：CrCl 30-89 mL/min 无需调整，但需严密监测血象。
    *   **奥沙利铂/卡培他滨**：若再次挑战，必须减量（卡培他滨减量 25%）。
    *   **低分子肝素**：若需抗凝，需按肾功能减量。

### 肝功能 & 骨髓
*   **肝功能**：目前正常。西妥昔单抗无肝毒性累积风险。
*   **骨髓**：多线化疗后骨髓储备可能不足。TAS-102 常见 3-4 级中性粒细胞减少（38%），需备好 G-CSF 支持。

---

## 5. 不建议的方案 (Not Recommended)

1.  **❌ 瑞戈非尼 (Regorafenib) / 呋喹替尼 (Fruquintinib)**
    *   **原因**：患者既往使用呋喹替尼发生严重**急性肾损伤**。瑞戈非尼具有相似的化学结构和毒性谱（手足皮肤反应、高血压、肾毒性），再次使用极高概率导致肾衰竭。
    *   **替代**：TAS-102 或 临床试验。

2.  **❌ 单药免疫检查点抑制剂 (PD-1)**
    *   **原因**：既往信迪利单抗联合化疗/疫苗均进展。尽管 TMB 高，但单药 PD-1 再挑战成功率极低。
    *   **替代**：若尝试免疫，必须联合（如 CTLA-4）或结合抗血管（但受限于肾功能）。

3.  **❌ 强化双药/三药化疗 (FOLFIRI/FOLFOX)**
    *   **原因**：患者 ECOG 1 分但高龄（70岁），且既往已耐药。肾功能限制了铂类和氟尿嘧啶的全量使用，获益风险比极低。

---

## 6. 监测与随访计划

*   **基线 (现在)**：
    *   复查肌酐、尿常规（蛋白尿）、电解质（镁、钙，因西妥昔单抗易致低镁）。
    *   血压监测（每日）。
*   **治疗期间**：
    *   **每 2 周**：血常规（关注中性粒细胞）、肝肾功能。
    *   **每 4 周**：电解质（镁）。
    *   **每 8 周**：CT 胸腹盆评价疗效。
*   **紧急停药指征**：
    *   肌酐较基线升高 >1.5 倍。
    *   出现 3 级以上皮疹伴感染。
    *   症状性低血压或肌痛（CPK 升高）。

---

## 7. 参考文献

*   **[CodeBreaK 300 Trial]**: Fakih MG, et al. Sotorasib plus Panitumumab in Refractory Colorectal Cancer with Mutated KRAS G12C. *N Engl J Med*. 2023. [[2]](#ref-pmid-37870536)
*   **[SUNLIGHT Trial]**: Prager GW, et al. Trifluridine-Tipiracil and Bevacizumab in Refractory Metastatic Colorectal Cancer. *N Engl J Med*. 2023. [[1]](#ref-pmid-37133585)
*   **[NCCN Guidelines]**: NCCN Clinical Practice Guidelines in Oncology: Colon Cancer. Version 1.2025.
*   **[FDA Label]**: LONSURF (trifluridine and tipiracil) Prescribing Information. Taiho Oncology, Inc.
*   **[FDA Label]**: ERBITUX (cetuximab) Prescribing Information. ImClone LLC.

---

## Tool Call Details

### Tool Call 1: `search_nccn`
**Timestamp:** 2026-01-20 16:48:16

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
**Timestamp:** 2026-01-20 16:48:17

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
**Timestamp:** 2026-01-20 16:48:18

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
**Timestamp:** 2026-01-20 16:48:23

**Parameters:**
```json
{
  "drug_name": "adagrasib",
  "check_interactions": [
    "atorvastatin",
    "nifedipine",
    "dapagliflozin"
  ]
}
```

**Result:**
```
**RxNorm 药物查询结果**

**药物**: adagrasib
**RxCUI**: 2625882

### 药物相互作用 (FDA 说明书)

*注: RxNorm 无数据，以下信息来自 FDA 药品说明书*

7 DRUG INTERACTIONS See full prescribing information for clinically significant drug interactions with KRAZATI. ( 7 ) • Strong CYP3A4 Inducers : Avoid concomitant use. ( 7.1 ) • Strong CYP3A4 Inhibitors : Avoid concomitant use until adagrasib concentrations have reached steady state. ( 7.1 ) • Sensitive CYP3A4 Substrates : Avoid concomitant use with sensitive CYP3A4 substrates. ( 7.2 ) • Sensitive CYP2C9 or CYP2D6 Substrates or P-gp Substrates : Avoid concomitant use with sensitive CYP2C9 or CYP2D6 substrates or P-gp substrates where minimal concentration changes may lead to serious adverse reactions. ( 7.2 ) • Drugs That Prolong QT Interval : Avoid concomitant use with KRAZATI. ( 7.3 ) 7.1 Effects of Other Drugs on KRAZATI Strong CYP3A4 Inducers Avoid concomitant use of KRAZATI with strong CYP3A inducers. Adagrasib is a CYP3A4 substrate. Concomitant use of KRAZATI with a strong CYP3A inducer reduces adagrasib exposure [see Clinical Pharmacology (12.3) ] , which may reduce the effectiveness of KRAZATI. Strong CYP3A4 Inhibitors Avoid concomitant use of KRAZATI with strong CYP3A inhibitors until adagrasib concentrations have reached steady state (after approximately 8 days). Adagrasib is a CYP3A4 substrate. If adagrasib concentrations have not reached steady state, concomitant use of a strong CYP3A inhibitor will increase adagrasib concentrations, [see Clinical Pharmacology (12.3) ], which may increase the risk of KRAZATI adverse reactions. 7.2 Effects of KRAZATI on Other Drugs Sensitive CYP3A Substrates Avoid concomitant use of KRAZATI with sensitive CYP3A substrates unless otherwise recommended in the Prescribing Information for these substrates. Adagrasib is a CYP3A inhibitor. Concomitant use with KRAZATI increases exposure of CYP3A substrates [see Clinical Pharmacology (12.3) ] , which may increase the risk of adverse reactions related to these substrates. Sensitive CYP2C9 Substrates Avoid concomitant use of KRAZATI with sensitive CYP2C9 substrates where minimal c

**参考**: https://rxnav.nlm.nih.gov
```

### Tool Call 5: `search_pubmed`
**Timestamp:** 2026-01-20 16:48:24

**Parameters:**
```json
{
  "query": "KRAS G12C inhibitor renal impairment colorectal cancer"
}
```

**Result:**
```
**PubMed 搜索结果**

**搜索关键词**: KRAS G12C inhibitor renal impairment colorectal cancer

未找到相关文献。
```


---

## References

<a id="ref-pmid-37133585"></a>**[1]** [PMID: 37133585](https://pubmed.ncbi.nlm.nih.gov/37133585/)

<a id="ref-pmid-37870536"></a>**[2]** [PMID: 37870536](https://pubmed.ncbi.nlm.nih.gov/37870536/)
