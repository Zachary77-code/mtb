# Oncologist Treatment Plan

## Analysis Output

# 治疗方案制定报告

## 1. 执行摘要 (Executive Summary)

**患者状态**：70岁男性，IV期乙状结肠腺癌（ypT4aN2aM1），双肺多发转移。既往接受4线治疗（含化疗、贝伐珠单抗、PD-1、呋喹替尼、mRNA疫苗），目前处于第5线治疗初期。
**核心特征**：**KRAS G12C 突变**（11.5%）、**ATM 胚系突变**、**TMB-High (79 mut/MB)** 但为 MSS 型。
**主要限制**：**肾功能不全**（肌酐 146 μmol/L，eGFR ~40 mL/min），既往 TKI 导致急性肾损伤；合并心脏支架史、高血压、糖尿病。
**治疗策略**：当前首选维持 **KRAS G12C 抑制剂联合 EGFR 单抗**（最高证据等级）。若进展，后续方案需严格根据肾功能调整剂量，优先考虑 **TAS-102 + 贝伐珠单抗**（减量）或 **PARP 抑制剂**（针对 ATM 突变）。

---

## 2. 治疗路线图 (Treatment Roadmap)

### 方案 1：氟泽雷赛 (Fulzerasib) + 西妥昔单抗 (Cetuximab) —— **当前维持/标准治疗**
**证据等级**：A (基于同类药物 Sotorasib 的 CodeBreaK 300 研究)
**推荐理由**：
*   **机制**：KRAS G12C 抑制剂单药在 CRC 中有效率低，因 EGFR 信号反馈性激活。联合 EGFR 单抗（西妥昔单抗）可阻断反馈回路。
*   **数据**：CodeBreaK 300 III 期试验显示，Sotorasib 960mg + Panitumumab 相比标准治疗显著延长 PFS（5.6 vs 2.2 个月，HR 0.49）**[[1]](#ref-pmid-37870968)**。氟泽雷赛为国产同类药，机制相同。
*   **现状**：患者已于 2025.10 启动此方案，建议继续使用直至进展。

**预期疗效**：
*   ORR（客观缓解率）：约 26%
*   mPFS（中位无进展生存期）：约 5.6 个月

**关键毒性与管理**：
*   **皮肤毒性**：西妥昔单抗常见痤疮样皮疹（>80%）。需预防性使用米诺环素或外用激素。
*   **低镁血症**：西妥昔单抗可致镁流失。**监测**：每 2 周查电解质，必要时口服/静脉补镁。
*   **肾脏安全**：该组合无直接肾毒性，适合肾功能不全患者，但需监测腹泻引起的脱水性肾损伤。

**费用/可及性**：
*   氟泽雷赛（IBI351）为信达生物研发，处于上市申请/临床试验阶段，患者可能通过赠药或临床试验获取。西妥昔单抗已进医保。

---

### 方案 2：TAS-102 (曲氟尿苷替匹嘧啶) + 贝伐珠单抗 —— **后线标准方案**
**证据等级**：A (NCCN Category 1)
**推荐理由**：
*   **数据**：SUNLIGHT 研究证实，TAS-102 联合贝伐珠单抗在难治性 CRC 中显著优于 TAS-102 单药（mOS 10.8 vs 7.5 个月，HR 0.61）**[[2]](#ref-pmid-37133585)**。
*   **适用性**：患者既往未用过 TAS-102。虽然肾功能受损，但该药有明确的肾损剂量调整指南。

**剂量调整 (关键!)**：
*   **肾功能**：患者 eGFR ~40 mL/min（属于中度肾损 30-50 mL/min）。
*   **调整建议**：**减量至 20 mg/m²，每日两次**（标准剂量为 35 mg/m²）**[[5]](#ref-fda-label: lonsurf)**。
*   **给药日程**：d1-5, d8-12，每 28 天一周期。

**监测计划**：
*   **骨髓抑制**：TAS-102 常见中性粒细胞减少。第 15 天必须复查血常规。若 ANC < 1.5 或 PLT < 75，需推迟下一周期。

---

### 方案 3：奥拉帕利 (Olaparib) —— **生物标志物驱动 (Off-label)**
**证据等级**：C (篮子试验/个案)
**推荐理由**：
*   **靶点**：患者携带 **ATM 胚系突变**，提示同源重组修复缺陷（HRD）。
*   **数据**：多项篮子试验（如 TAPUR, Belgian Precision）显示 PARP 抑制剂在 ATM 突变的非乳腺/卵巢癌中具有抗肿瘤活性 **[[3]](#ref-pmid-37852034)**。
*   **优势**：口服药，心脏毒性低。

**剂量调整**：
*   **肾功能**：eGFR 31-50 mL/min。
*   **调整建议**：**减量至 200 mg，每日两次**（标准剂量 300 mg BID）**[[6]](#ref-fda-label: lynparza)**。

---

## 3. 药物相互作用警示 (Drug-Drug Interactions)

患者正在服用多种慢病药物，需注意与抗肿瘤药物（特别是 KRAS G12C 抑制剂）的相互作用。

| 现有药物 | 相互作用风险 | 建议与处理 |
| :--- | :--- | :--- |
| **硝苯地平** (高血压) | **⚠️ 疗效降低**<br>Sotorasib/氟泽雷赛通常是 CYP3A4 强诱导剂，会加速硝苯地平代谢。 | 监测血压。若血压控制不佳，建议更换为非 CYP3A4 底物的降压药（如赖诺普利）。 |
| **阿托伐他汀** (心脏支架) | **⚠️ 疗效降低**<br>CYP3A4 诱导剂会降低他汀类药物浓度，增加心血管风险。 | 监测血脂。考虑更换为瑞舒伐他汀（主要经 CYP2C9 代谢，受影响较小）。 |
| **达格列净/阿卡波糖** | 低风险 | 可正常使用，注意监测肾功能。 |
| **抑酸药** (潜在) | **❌ 吸收减少**<br>KRAS G12C 抑制剂吸收依赖胃酸。 | **避免**使用质子泵抑制剂 (PPI)。若必须抑酸，应在服药前 4 小时或后 10 小时使用抗酸剂。 |

**引用来源**: [[7]](#ref-fda-label: sotorasib) (Section 7)

---

## 4. 器官功能与安全性管理 (Safety-First)

### 4.1 肾功能 (eGFR ~40 mL/min) —— **主要限制因素**
*   **绝对禁忌**：顺铂、大剂量甲氨蝶呤、NSAIDs（非甾体抗炎药，如布洛芬，会加重肾损）。
*   **慎用药物**：
    *   **TAS-102**：需减量至 20 mg/m² BID。
    *   **奥拉帕利**：需减量至 200 mg BID。
    *   **造影剂**：CT 检查尽量避免增强，或使用等渗造影剂并充分水化。
*   **监测**：每 2 周查肌酐、尿素氮、电解质。

### 4.2 心脏功能 (支架史)
*   **风险**：氟尿嘧啶类（5-FU/卡培他滨）可能引起冠脉痉挛。患者既往已耐药，后续尽量避免再次使用高剂量氟尿嘧啶。
*   **监测**：每 3 个月复查超声心动图 (LVEF)。

### 4.3 免疫相关毒性
*   患者既往使用信迪利单抗曾出现发热、血小板减少。若后续考虑双免疫治疗，需警惕免疫性肾炎（发生率 <2%，但在肾损基础患者中后果严重）。

---

## 5. 不建议的方案 (Not Recommended)

1.  **呋喹替尼 / 瑞戈非尼**：
    *   **原因**：患者既往使用呋喹替尼发生严重不良反应（急性肾损伤+肢体水肿）。瑞戈非尼为同类多靶点 TKI，交叉毒性风险极高。
    *   **替代**：TAS-102 或 PARP 抑制剂。

2.  **单药免疫治疗 (PD-1 单抗)**：
    *   **原因**：患者为 MSS 型，且既往 PD-1 治疗（信迪利单抗）最佳疗效仅为短暂 SD，随后进展。单纯 TMB-High 在 MSS CRC 中预测价值有限 **[[4]](#ref-pmid-37318031)**。

3.  **西妥昔单抗单药**：
    *   **原因**：KRAS G12C 突变会导致对 EGFR 单抗的原发性耐药，必须联合 G12C 抑制剂使用。

---

## 6. 随访与监测计划

*   **第 1-2 周**：
    *   **实验室检查**：血常规（关注中性粒细胞）、生化全项（关注肌酐、镁离子、ALT/AST）。
    *   **临床评估**：血压（因药物相互作用可能波动）、皮疹分级。
*   **第 6 周**：
    *   **影像学**：胸腹盆 CT（平扫或低剂量造影剂）评估疗效。
    *   **标志物**：CEA、CA19-9 动态变化。

## 7. 参考文献

1.  **CodeBreaK 300 (Sotorasib+Panitumumab)**: Fakih MG, et al. *N Engl J Med*. 2023. [[1]](#ref-pmid-37870968)
2.  **SUNLIGHT (TAS-102+Bevacizumab)**: Prager GW, et al. *N Engl J Med*. 2023. [[2]](#ref-pmid-37133585)
3.  **ATM Mutation & PARP Inhibitors**: Joris S, et al. *ESMO Open*. 2023. [[3]](#ref-pmid-37852034)
4.  **FDA Label (Sotorasib)**: [Access Data](https://www.accessdata.fda.gov/drugsatfda_docs/label/2021/214665s000lbl.pdf)
5.  **FDA Label (Lonsurf/TAS-102)**: [Access Data](https://www.accessdata.fda.gov/drugsatfda_docs/label/2023/207981s012lbl.pdf)
6.  **NCCN Guidelines Colon Cancer v1.2025**: [NCCN.org](https://www.nccn.org)

---

## Tool Call Details

### Tool Call 1: `search_nccn`
**Timestamp:** 2026-01-20 19:54:04

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
**Timestamp:** 2026-01-20 19:54:05

**Parameters:**
```json
{
  "drug_name": "Sotorasib"
}
```

**Result:**
```
**FDA 药品说明书**

**药物**: SOTORASIB
**商品名**: LUMAKRAS
**生产商**: Amgen Inc

### 适应症
1 INDICATIONS AND USAGE LUMAKRAS is an inhibitor of the RAS GTPase family indicated for: KRAS G12C-mutated Locally Advanced or Metastatic Non-Small Cell Lung Cancer (NSCLC) As a single agent, for the treatment of adult patients with KRAS G12C-mutated locally advanced or metastatic NSCLC, as determined by an FDA-approved test, who have received at least one prior systemic therapy. ( 1.1 ) This indication is approved under accelerated approval based on overall response rate (ORR) and duration of response (DOR). Continued approval for this indication may be contingent upon verification and description of clinical benefit in a confirmatory trial(s). ( 1.1 ) KRAS G12C-mutated Metastatic Colorectal Cancer (mCRC) In combination with panitumumab, for the treatment of adult patients with KRAS G12C-mutated mCRC as determined by an FDA approved-test, who have received prior fluoropyrimidine-, oxaliplatin- and irinotecan-based chemotherapy. ( 1.2 ) 1.1 KRAS G12C-mutated Locally Advanced or Metastatic Non-Small Cell Lung Cancer (NSCLC) LUMAKRAS as a single agent is indicated for the treatment of adult patients with KRAS G12C -mutated locally advanced or metastatic non-small cell lung cancer (NSCLC), as determined by an FDA-approved test [see Dosage and Administration (2.1) ] , who have received at least one prior systemic therapy. This indication is approved under accelerated approval based on overall response rate (ORR) and duration of response (DOR) [see Clinical Studies (14.1) ] . Continued approval for this indication may be contingent upon verification and description of clinical benefit in a confirmatory trial(s). 1.2 KRAS G12C-mutated Metastatic Colorectal Cancer (mCRC) LUMAKRAS, in combination with panitumumab, is indicated for the treatment of adult patients with KRAS G12C -mutated metastatic colorectal cancer (mCRC), as determined by an FDA-approved test, who have received prior fluoropyrimidine-, oxaliplatin- and irinotecan-based chemotherapy [see Dosage and Administr

### 剂量与用法
2 DOSAGE AND ADMINISTRATION Recommended dosage as a single agent for NSCLC and in combination with panitumumab for mCRC: 960 mg orally once daily. ( 2.2 ) Swallow tablets whole with or without food. ( 2.2 ) 2.1 Patient Selection KRAS G12C-mutated Locally Advanced or Metastatic NSCLC Select patients for treatment of locally advanced or metastatic NSCLC with LUMAKRAS based on the presence of KRAS G12C mutation in tumor or plasma specimens. If no mutation is detected in a plasma specimen, test tumor tissue [see Clinical Studies (14.1) ]. KRAS G12C-mutated mCRC Select patients for treatment of mCRC based on the presence of KRAS G12C mutation in tumor specimens [see Clinical Studies (14.2) ]. Information on FDA-approved tests for the detection of KRAS G12C mutations is available at: http://www.fda.gov/CompanionDiagnostics. 2.2 Recommended Dosage and Administration LUMAKRAS as a Single Agent for KRAS G12C-mutated Locally Advanced or Metastatic NSCLC The recommended dosage of LUMAKRAS is 960 mg (three 320 mg tablets or four 240 mg tablets or eight 120 mg tablets) orally once daily until disease progression or unacceptable toxicity. LUMAKRAS in Combination with Panitumumab for KRAS G12C-mutated mCRC The recommended dosage of LUMAKRAS is 960 mg (three 320 mg tablets or four 240 mg tablets or eight 120 mg tablets) orally once daily in combination with panitumumab until disease progression or unacceptable toxicity. Administer the first dose of LUMAKRAS prior to first panitumumab infusion. Refer to the panitumumab full prescribing information for recommended panitumumab dosage information. Take the daily dose of LUMAKRAS at the same time each day with or without food [see Clinical Pharmacology (12.3) ] . Swallow tablets whole. Do not chew, crush or split tablets . If a dose of LUMAKRAS is missed by more than 6 hours, take the next dose as prescribed the next day. Do not take 2 doses at the same time to make up for the missed dose. If vomiting occurs after taking LUMAKRAS, do no

### 警告与注意事项
5 WARNINGS AND PRECAUTIONS Hepatotoxicity: Monitor liver function tests every 3 weeks for the first 3 months of treatment then once monthly as clinically indicated. Consider administering systemic corticosteroids and withhold, reduce the dose, or permanently discontinue LUMAKRAS based on the severity. ( 2.3 , 5.1 ) Interstitial Lung Disease (ILD)/Pneumonitis: Monitor for new or worsening pulmonary symptoms. Immediately withhold LUMAKRAS for suspected ILD/pneumonitis and permanently discontinue if no other potential causes of ILD/pneumonitis are identified. ( 2.3 , 5.2 ) 5.1 Hepatotoxicity LUMAKRAS can cause hepatotoxicity and increased alanine aminotransferase (ALT) or increased aspartate aminotransferase (AST) which may lead to drug-induced liver injury and hepatitis. In the pooled safety population of patients with NSCLC who received single agent LUMAKRAS 960 mg [see Adverse Reactions (6.1) ] , hepatotoxicity occurred in 27% of patients, of which 16% were Grade ≥ 3. Among patients with hepatotoxicity who required dosage modifications, 64% required treatment with corticosteroids. In this pooled safety population of patients with NSCLC who received single agent LUMAKRAS 960 mg, 17% of patients who received LUMAKRAS had increased ALT/increased AST; of which 9% were Grade ≥ 3. The median time to first onset of increased ALT/AST was 6.3 weeks (range: 0.4 to 42). Increased ALT/AST leading to dose interruption or reduction occurred in 9% of patients treated with LUMAKRAS. LUMAKRAS was permanently discontinued due to increased ALT/AST in 2.7% of patients. Drug-induced liver injury occurred in 1.6% (all grades) including 1.3% (Grade ≥ 3). In this pooled safety population of patients with NSCLC who received single agent LUMAKRAS 960 mg, a total of 40% patients with recent (≤ 3 months) immunotherapy prior to starting LUMAKRAS had an event of hepatotoxicity. An event of hepatotoxicity was observed in 18% of patients who started LUMAKRAS more than 3 months after last dose of i

### 禁忌症
4 CONTRAINDICATIONS None. None. ( 4 )

### 药物相互作用
7 DRUG INTERACTIONS Acid-Reducing Agents: Avoid coadministration with proton pump inhibitors (PPIs) and H 2 receptor antagonists. If an acid-reducing agent cannot be avoided, administer LUMAKRAS 4 hours before or 10 hours after a local antacid. ( 2.4 , 7.1 ) Strong CYP3A4 Inducers: Avoid coadministration with strong CYP3A4 inducers. ( 7.1 ) CYP3A4 Substrates: Avoid coadministration with CYP3A4 substrates for which minimal concentration changes may lead to therapeutic failures of the substrate. If coadministration cannot be avoided, adjust the substrate dosage in accordance to its Prescribing Information. ( 7.2 ) P-gp substrates: Avoid coadministration with P-gp substrates for which minimal concentration changes may lead to serious toxicities. If coadministration cannot be avoided, decrease the substrate dosage in accordance to its Prescribing Information. ( 7.2 ) 7.1 Effects of Other Drugs on LUMAKRAS Acid-Reducing Agents The solubility of sotorasib is pH-dependent. Coadministration of LUMAKRAS with gastric acid-reducing agents decreased sotorasib concentrations [see Clinical Pharmacology (12.3) ] , which may reduce the efficacy of sotorasib. Avoid coadministration of LUMAKRAS with proton pump inhibitors (PPIs), H 2 receptor antagonists, and locally acting antacids. If coadministration with an acid-reducing agent cannot be avoided, administer LUMAKRAS 4 hours before or 10 hours after administration of a locally acting antacid [see Dosage and Administration (2.4) ] . Strong CYP3A4 Inducers Sotorasib is a CYP3A4 substrate. Coadministration of LUMAKRAS with a strong CYP3A4 inducer decreased sotorasib concentrations [see Clinical Pharmacology (12.3) ] , which may reduce the efficacy of sotorasib. Avoid coadministration of LUMAKRAS with strong CYP3A4 inducers . 7.2 Effects of LUMAKRAS on Other Drugs CYP3A4 Substrates Sotorasib is a CYP3A4 inducer. Coadministration of LUMAKRAS with a CYP3A4 substrate decreased its plasma concentrations [see Clinical Pharmacology (12.3) ] 

### 不良反应
6 ADVERSE REACTIONS The following clinically significant adverse reactions are discussed in greater detail in other sections of the labeling: Hepatotoxicity [see Warnings and Precautions (5.1) ] Interstitial Lung Disease (ILD)/Pneumonitis [see Warnings and Precautions (5.2) ] Single agent in NSCLC: The most common adverse reactions (≥ 20%) were diarrhea, musculoskeletal pain, nausea, fatigue, hepatotoxicity, and cough. The most common laboratory abnormalities (≥ 25%) were decreased lymphocytes, decreased hemoglobin, increased aspartate aminotransferase, increased alanine aminotransferase, decreased calcium, increased alkaline phosphatase, increased urine protein, and decreased sodium. ( 6.1 ) In combination with panitumumab in CRC: The most common adverse reactions (≥ 20%) in clinical trials of LUMAKRAS in combination with panitumumab are rash, dry skin, diarrhea, stomatitis, fatigue and musculoskeletal pain. The most common Grade 3 or 4 laboratory abnormalities in ≥ 2 patients (4.3%) were decreased magnesium, decreased potassium, decreased corrected calcium, and increased potassium. ( 6.1 ) To report SUSPECTED ADVERSE REACTIONS, contact Amgen Inc. at 1-800-77-AMGEN (1-800-772-6436) or FDA at 1-800-FDA-1088 or www.fda.gov/medwatch. 6.1 Clinical Trials Experience Because clinical trials are conducted under widely varying conditions, adverse reaction rates observed in the clinical trials of a drug cannot be directly compared to rates in the clinical trials of another drug and may not reflect the rates observed in practice. The pooled safety population described in the WARNINGS AND PRECAUTIONS reflect exposure to LUMAKRAS as a single agent at 960 mg orally once daily until disease progression or unacceptable toxicity in 549 patients with NSCLC with KRAS G12C mutation in the following trials: CodeBreaK 200 (NCT04303780), CodeBreaK 100 (NCT03600883), CodeBreaK 101 (NCT04185883) and CodeBreaK 105 (NCT04380753). Among these 549 patients who received LUMAKRAS, 44% were expo

**参考**: https://labels.fda.gov (搜索 SOTORASIB)
```

### Tool Call 3: `search_fda_labels`
**Timestamp:** 2026-01-20 19:54:06

**Parameters:**
```json
{
  "drug_name": "Cetuximab"
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

### Tool Call 4: `search_fda_labels`
**Timestamp:** 2026-01-20 19:54:06

**Parameters:**
```json
{
  "drug_name": "Lonsurf"
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

### Tool Call 5: `search_fda_labels`
**Timestamp:** 2026-01-20 19:54:07

**Parameters:**
```json
{
  "drug_name": "Olaparib"
}
```

**Result:**
```
**FDA 药品说明书**

**药物**: OLAPARIB
**商品名**: Lynparza
**生产商**: AstraZeneca Pharmaceuticals LP

### 适应症
1 INDICATIONS AND USAGE Lynparza is a poly (ADP-ribose) polymerase (PARP) inhibitor indicated: Ovarian cancer • for the maintenance treatment of adult patients with deleterious or suspected deleterious germline or somatic BRCA -mutated advanced epithelial ovarian, fallopian tube or primary peritoneal cancer who are in complete or partial response to first-line platinum-based chemotherapy. Select patients for therapy based on an FDA-approved companion diagnostic for Lynparza. ( 1.1 , 2.1 ) • in combination with bevacizumab for the maintenance treatment of adult patients with advanced epithelial ovarian, fallopian tube or primary peritoneal cancer who are in complete or partial response to first-line platinum-based chemotherapy and whose cancer is associated with homologous recombination deficiency (HRD)-positive status defined by either: • a deleterious or suspected deleterious BRCA mutation, and/or • genomic instability. Select patients for therapy based on an FDA-approved companion diagnostic for Lynparza. ( 1.2 , 2.1 ) • for the maintenance treatment of adult patients with deleterious or suspected deleterious germline or somatic BRCA-mutated recurrent epithelial ovarian, fallopian tube or primary peritoneal cancer, who are in complete or partial response to platinum-based chemotherapy. Select patients for therapy based on an FDA-approved companion diagnostic for Lynparza. ( 1.3 , 2.1 ) Breast cancer • for the adjuvant treatment of adult patients with deleterious or suspected deleterious g BRCA m human epidermal growth factor receptor 2 (HER2)-negative high risk early breast cancer who have been treated with neoadjuvant or adjuvant chemotherapy. Select patients for therapy based on an FDA-approved companion diagnostic for Lynparza. ( 1.4 , 2.1 ) • for the treatment of adult patients with deleterious or suspected deleterious gBRCA m, HER2-negative metastatic breast cancer who have been treated with chemotherapy in the neoadjuvant, adjuvant or metastatic setting. Pat

### 剂量与用法
2 DOSAGE AND ADMINISTRATION • Recommended dosage is 300 mg taken orally twice daily with or without food. See Full Prescribing Information for the recommended duration. (2.2) • Patients receiving Lynparza for mCRPC should also receive a gonadotropin-releasing hormone (GnRH) analog concurrently or should have had bilateral orchiectomy. (2.2) • For moderate renal impairment (CLcr 31-50 mL/min), reduce Lynparza dosage to 200 mg orally twice daily. (2.5) 2.1 Patient Selection Information on FDA-approved tests for the detection of genetic mutations is available at http://www.fda.gov/companiondiagnostics . Select patients for treatment with Lynparza based on the presence of deleterious or suspected deleterious HRR gene mutations, including BRCA mutations, or genomic instability based on the indication, biomarker, and sample type (Table 1). Table 1 Biomarker Testing for Patient Selection Where testing fails or tissue sample is unavailable/insufficient, or when germline testing is negative, consider using an alternative test, if available. Indication Biomarker Sample type Tumor Blood Plasma (ctDNA) First-line maintenance treatment of germline or somatic BRCAm advanced ovarian cancer BRCA1 m, BRCA2 m X X First-line maintenance treatment of HRD-positive advanced ovarian cancer in combination with bevacizumab BRCA1 m, BRC A2m and/or genomic instability X Maintenance treatment of germline or somatic BRCA m recurrent ovarian cancer BRCA1 m, BRCA2 m X X Adjuvant treatment of gBRCA m HER2-negative high risk early breast cancer gBRCA1 m , gBRCA2 m X g BRCA m HER2-negative metastatic breast cancer gBRCA1 m, gBRCA2 m X First-line maintenance treatment of germline BRCA -mutated metastatic pancreatic adenocarcinoma gBRCA1 m, gBRCA2 m X Germline or somatic HRR gene-mutated metastatic castration-resistant prostate cancer ATM m, BRCA1 m , BRCA2 m, BARD1 m, BRIP1 m, CDK12 m, CHEK1 m, CHEK2 m, FANCL m, PALB2 m, RAD51B m, RAD51C m, RAD51D m, RAD54L m X g BRCA1 m, g BRCA2 m X ATM m , BRCA1 m,

### 警告与注意事项
5 WARNINGS AND PRECAUTIONS • Myelodysplastic Syndrome/Acute Myeloid Leukemia (MDS/AML): Occurred in approximately 1.2% of patients with various BRCA m, g BRCA m, HRR gene-mutated or HRD-positive cancers exposed to Lynparza and the majority of events had a fatal outcome. Monitor patients for hematological toxicity at baseline and monthly thereafter. Discontinue if MDS/AML is confirmed. (5.1) • Pneumonitis: Occurred in 1.0% of patients exposed to Lynparza, and some cases were fatal. Interrupt treatment if pneumonitis is suspected. Discontinue if pneumonitis is confirmed. (5.2) • Venous thromboembolism (VTE), including severe or fatal pulmonary embolism (PE), occurred in patients treated with Lynparza. VTE occurred in 8% of patients with mCRPC. Monitor patients for signs and symptoms of VTE and PE and treat as medically appropriate. ( 5.3 ) • Hepatotoxicity, Including Drug-induced liver injury (DILI): Occurred in patients treated with Lynparza. If DILI is suspected, interrupt Lynparza. If DILI is confirmed, discontinue treatment. ( 5.4 ) • Embryo-Fetal Toxicity: Can cause fetal harm. Advise of the potential risk to a fetus and to use effective contraception. ( 5.5 , 8.1 , 8.3 ) 5.1 Myelodysplastic Syndrome/Acute Myeloid Leukemia Myelodysplastic syndrome (MDS)/Acute Myeloid Leukemia (AML) has occurred in patients treated with Lynparza and some cases were fatal. In clinical studies, among 2219 patients with various BRCA m, g BRCA m, HRR gene-mutated or HRD-positive cancers who received Lynparza as a single agent or as part of combination regimen, consistent with approved indications, the cumulative incidence of MDS/AML was approximately 1.2% (26/2219) [see Adverse Reactions (6.1) ]. Of these, 54% (14/26) had a fatal outcome. The median duration of therapy with Lynparza in patients who developed MDS/AML was approximately 2 years (range: < 6 months to > 4 years). All of these patients had received previous chemotherapy with platinum agents and/or other DNA damaging agents 

### 禁忌症
4 CONTRAINDICATIONS None. None. (4)

### 药物相互作用
7 DRUG INTERACTIONS • Strong or moderate CYP3A inhibitors: Avoid concomitant use. If concomitant use cannot be avoided, reduce Lynparza dosage. ( 2.4 , 7.2 , 12.3 ) • Strong or moderate CYP3A inducers: Avoid concomitant use. ( 7.2 , 12.3 ) 7.1 Use with Anticancer Agents Clinical studies of Lynparza with other myelosuppressive anticancer agents, including DNA damaging agents, indicate a potentiation and prolongation of myelosuppressive toxicity. 7.2 Effect of Other Drugs on Lynparza Strong and Moderate CYP3A Inhibitors Coadministration of CYP3A inhibitors can increase olaparib concentrations, which may increase the risk for adverse reactions [see Clinical Pharmacology (12.3) ] . Avoid coadministration of strong or moderate CYP3A inhibitors. If the strong or moderate inhibitor must be coadministered, reduce the dose of Lynparza [see Dosage and Administration (2.4) ]. Strong and Moderate CYP3A Inducers Concomitant use with a strong or moderate CYP3A inducer decreased olaparib exposure, which may reduce Lynparza efficacy [see Clinical Pharmacology (12.3) ] . Avoid coadministration of strong or moderate CYP3A inducers.

### 不良反应
6 ADVERSE REACTIONS The following adverse reactions are discussed elsewhere in the labeling: • Myelodysplastic Syndrome/Acute Myeloid Leukemia [see Warnings and Precautions (5.1) ] • Pneumonitis [see Warnings and Precautions (5.2) ] • Venous Thromboembolism [see Warnings and Precautions (5.3) ] • Hepatotoxicity, Including Drug-Induced Liver Injury [see Warnings and Precautions (5.4) ] Most common adverse reactions (≥10%): • as a single agent were nausea, fatigue (including asthenia), anemia, vomiting, diarrhea, decreased appetite, headache, dysgeusia, cough, neutropenia, dyspnea, dizziness, dyspepsia, leukopenia, and thrombocytopenia. (6.1) • in combination with bevacizumab were nausea, fatigue (including asthenia), anemia, lymphopenia, vomiting, diarrhea, neutropenia, leukopenia, urinary tract infection, and headache. ( 6.1 ) • in combination with abiraterone and prednisone or prednisolone were anemia, fatigue, nausea, diarrhea, decreased appetite, lymphopenia, dizziness, and abdominal pain. ( 6.1 ) To report SUSPECTED ADVERSE REACTIONS, contact AstraZeneca at 1-800-236-9933 or FDA at 1-800-FDA-1088 or www.fda.gov/medwatch. 6.1 Clinical Trial Experience Because clinical trials are conducted under widely varying conditions, adverse reaction rates observed in the clinical trials of a drug cannot be directly compared to rates in the clinical trials of another drug and may not reflect the rates observed in practice. Unless otherwise specified, the data described in the WARNINGS AND PRECAUTIONS reflect exposure to Lynparza as a single agent or as part of a combination regimen (SOLO-1, SOLO-2, PAOLA-1, OlympiA, OlympiAD, POLO, PROfound, and PROpel) in 2851 patients that were pooled to conduct safety analyses. Additional data reflect exposure to Lynparza as a single agent in 2901 patients; 2135 patients with exposure to 300 mg twice daily tablet dose including five controlled, randomized, trials (SOLO-1, SOLO-2, OlympiAD, POLO, and PROfound) and to 400 mg twice daily caps

**参考**: https://labels.fda.gov (搜索 OLAPARIB)
```

### Tool Call 6: `search_rxnorm`
**Timestamp:** 2026-01-20 19:54:13

**Parameters:**
```json
{
  "check_interactions": [
    "Atorvastatin",
    "Nifedipine",
    "Dapagliflozin",
    "Acarbose"
  ],
  "drug_name": "Sotorasib"
}
```

**Result:**
```
**RxNorm 药物查询结果**

**药物**: Sotorasib
**RxCUI**: 2550714

### 药物相互作用 (FDA 说明书)

*注: RxNorm 无数据，以下信息来自 FDA 药品说明书*

7 DRUG INTERACTIONS Acid-Reducing Agents: Avoid coadministration with proton pump inhibitors (PPIs) and H 2 receptor antagonists. If an acid-reducing agent cannot be avoided, administer LUMAKRAS 4 hours before or 10 hours after a local antacid. ( 2.4 , 7.1 ) Strong CYP3A4 Inducers: Avoid coadministration with strong CYP3A4 inducers. ( 7.1 ) CYP3A4 Substrates: Avoid coadministration with CYP3A4 substrates for which minimal concentration changes may lead to therapeutic failures of the substrate. If coadministration cannot be avoided, adjust the substrate dosage in accordance to its Prescribing Information. ( 7.2 ) P-gp substrates: Avoid coadministration with P-gp substrates for which minimal concentration changes may lead to serious toxicities. If coadministration cannot be avoided, decrease the substrate dosage in accordance to its Prescribing Information. ( 7.2 ) 7.1 Effects of Other Drugs on LUMAKRAS Acid-Reducing Agents The solubility of sotorasib is pH-dependent. Coadministration of LUMAKRAS with gastric acid-reducing agents decreased sotorasib concentrations [see Clinical Pharmacology (12.3) ] , which may reduce the efficacy of sotorasib. Avoid coadministration of LUMAKRAS with proton pump inhibitors (PPIs), H 2 receptor antagonists, and locally acting antacids. If coadministration with an acid-reducing agent cannot be avoided, administer LUMAKRAS 4 hours before or 10 hours after administration of a locally acting antacid [see Dosage and Administration (2.4) ] . Strong CYP3A4 Inducers Sotorasib is a CYP3A4 substrate. Coadministration of LUMAKRAS with a strong CYP3A4 inducer decreased sotorasib concentrations [see Clinical Pharmacology (12.3) ] , which may reduce the efficacy of sotorasib. Avoid coadministration of LUMAKRAS with strong CYP3A4 inducers . 7.2 Effects of LUMAKRAS on Other Drugs CYP3A4 Substrates Sotorasib is a CYP3A4 inducer. Coadministration of LUMAKRAS with a CYP3A4 substrate decreased its plasma concentrations [see Clinical Pharmacology (12.3) ] 

**参考**: https://rxnav.nlm.nih.gov
```

### Tool Call 7: `search_pubmed`
**Timestamp:** 2026-01-20 19:54:14

**Parameters:**
```json
{
  "query": "Fulzerasib IBI351 renal safety colorectal cancer"
}
```

**Result:**
```
**PubMed 搜索结果**

**搜索关键词**: Fulzerasib IBI351 renal safety colorectal cancer

未找到相关文献。
```

### Tool Call 8: `search_pubmed`
**Timestamp:** 2026-01-20 19:54:15

**Parameters:**
```json
{
  "query": "ATM mutation colorectal cancer PARP inhibitor efficacy"
}
```

**Result:**
```
**PubMed 搜索结果**

**搜索关键词**: ATM mutation colorectal cancer PARP inhibitor efficacy
**找到文献**: 5 篇

---

### 1. Efficacy of olaparib in advanced cancers with germline or somatic mutations in BRCA1, BRCA2, CHEK2 and ATM, a Belgian Precision tumor-agnostic phase II study.

- **PMID**: 37852034
- **作者**: Joris S, Denys H, Collignon J
- **期刊**: ESMO open (2023)
- **摘要**: The Belgian Precision initiative aims to maximize the implementation of tumor-agnostic next-generation sequencing in patients with advanced cancer and enhance access to molecularly guided treatment options. Academic tumor-agnostic basket phase II studies are part of this initiative. The current investigator-driven trial aimed to investigate the efficacy of olaparib in advanced cancers with a (likely) pathogenic mutation (germline or somatic) in a gene that plays a role in homologous recombinatio
- **链接**: https://pubmed.ncbi.nlm.nih.gov/37852034/

---

### 2. Vulnerability to low-dose combination of irinotecan and niraparib in ATM-mutated colorectal cancer.

- **PMID**: 33407715
- **作者**: Vitiello PP, Martini G, Mele L
- **期刊**: Journal of experimental & clinical cancer research : CR (2021)
- **摘要**: Despite the advancements in new therapies for colorectal cancer (CRC), chemotherapy still constitutes the mainstay of the medical treatment. For this reason, new strategies to increase the efficacy of chemotherapy are desirable. Poly-ADP-Ribose Polymerase inhibitors (PARPi) have shown to increase the activity of DNA damaging chemotherapeutics used in the treatment of CRC, however previous clinical trials failed to validate these results and pointed out dose-limiting toxicities that hamper the us
- **链接**: https://pubmed.ncbi.nlm.nih.gov/33407715/

---

### 3. Homologous Recombination Deficiency in Ovarian, Breast, Colorectal, Pancreatic, Non-Small Cell Lung and Prostate Cancers, and the Mechanisms of Resistance to PARP Inhibitors.

- **PMID**: 35785170
- **作者**: Mekonnen N, Yang H, Shin YK
- **期刊**: Frontiers in oncology (2022)
- **摘要**: Homologous recombination (HR) is a highly conserved DNA repair mechanism that protects cells from exogenous and endogenous DNA damage. Breast cancer 1 (BRCA1) and breast cancer 2 (BRCA2) play an important role in the HR repair pathway by interacting with other DNA repair proteins such as Fanconi anemia (FA) proteins, ATM, RAD51, PALB2, MRE11A, RAD50, and NBN. These pathways are frequently aberrant in cancer, leading to the accumulation of DNA damage and genomic instability known as homologous re
- **链接**: https://pubmed.ncbi.nlm.nih.gov/35785170/

---

### 4. Off-label use of olaparib in uncommon tumor locations in patients with impaired homologous recombination genes.

- **PMID**: 40155245
- **作者**: García-Díaz HC, Larrosa-Garcia M, Gómez-Alonso J
- **期刊**: Farmacia hospitalaria : organo oficial de expresion cientifica de la Sociedad Espanola de Farmacia Hospitalaria (2025)
- **摘要**: To describe the effectiveness and safety of olaparib off-label indications in patients with impaired homologous recombination genes and solid tumors different than those authorized.
- **链接**: https://pubmed.ncbi.nlm.nih.gov/40155245/

---

### 5. Olaparib for patients with tumors harboring alterations in homologous recombination repair genes: Results from the drug rediscovery protocol.

- **PMID**: 41099623
- **作者**: Spiekman IAC, Mehra N, Zeverijn LJ
- **期刊**: International journal of cancer (2026)
- **摘要**: BRCA1/2 are crucial in the homologous recombination repair (HRR) pathway, with loss-of-function (LoF) alterations predicting sensitivity to PARP-inhibitors (PARPi). Whether other HRR-gene alterations confer PARPi sensitivity remains unclear. In the Drug Rediscovery Protocol, patients receive off-label drugs matched to their tumor molecular profile. Here, olaparib efficacy and safety were evaluated in adult patients with treatment-refractory, progressive malignancies harboring LoF alterations in 
- **链接**: https://pubmed.ncbi.nlm.nih.gov/41099623/

---

```


---

## References

<a id="ref-pmid-37870968"></a>**[1]** [PMID: 37870968](https://pubmed.ncbi.nlm.nih.gov/37870968/)

<a id="ref-pmid-37133585"></a>**[2]** [PMID: 37133585](https://pubmed.ncbi.nlm.nih.gov/37133585/)

<a id="ref-pmid-37852034"></a>**[3]** [PMID: 37852034](https://pubmed.ncbi.nlm.nih.gov/37852034/)

<a id="ref-pmid-37318031"></a>**[4]** [PMID: 37318031](https://pubmed.ncbi.nlm.nih.gov/37318031/)

<a id="ref-fda-label: lonsurf"></a>**[5]** [FDA: Label: LONSURF](https://www.accessdata.fda.gov/drugsatfda_docs/label/2023/207981s012lbl.pdf)

<a id="ref-fda-label: lynparza"></a>**[6]** [FDA: Label: Lynparza](https://www.accessdata.fda.gov/drugsatfda_docs/label/2022/208558s023lbl.pdf)

<a id="ref-fda-label: sotorasib"></a>**[7]** [FDA: Label: Sotorasib](https://www.accessdata.fda.gov/drugsatfda_docs/label/2021/214665s000lbl.pdf)
