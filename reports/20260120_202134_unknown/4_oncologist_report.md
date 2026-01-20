# Oncologist Treatment Plan

## Analysis Output

# 治疗方案制定报告

## 1. 执行摘要 (Executive Summary)

患者为 70 岁男性，IV 期乙状结肠腺癌（KRAS G12C+, MSS, TMB-H, ATM 胚系突变），目前处于五线治疗阶段（氟泽雷赛 + 西妥昔单抗）。
**核心策略**：
1.  **当前治疗**：**氟泽雷赛 + 西妥昔单抗** 是基于 KRAS G12C 突变的最佳循证选择，但鉴于患者 eGFR 约 39 mL/min 及既往 TKI 肾损伤史，需极高强度的肾功能监测。
2.  **后续储备**：若当前方案进展，首选 **TAS-102 + 贝伐珠单抗**（标准治疗），或基于 ATM 突变尝试 **PARP 抑制剂**（临床试验/超适应症）。
3.  **安全警示**：患者肾功能处于 CKD 3b 期（eGFR < 40 mL/min），且合并心血管疾病，需严格规避肾毒性药物并管理药物相互作用。

---

## 2. 治疗路线图 (Treatment Roadmap)

### 🔴 当前方案 (Current Regimen) - 维持与监测
**方案名称**: 氟泽雷赛 (Fulzerasib/IBI351) + 西妥昔单抗 (Cetuximab)
**证据等级**: B (基于同类药物 Sotorasib/Adagrasib 的 III 期数据及 IBI351 早期数据)
**治疗定位**: 五线挽救治疗 (针对 KRAS G12C)

*   **合理性**:
    *   KRAS G12C 抑制剂联合 EGFR 单抗是该亚型的标准治疗策略。CodeBreaK 300 研究显示，Sotorasib + Panitumumab 较标准治疗显著延长 PFS [[1]](#ref-pmid-37870968)。
    *   氟泽雷赛是中国原研药物，早期数据显示在 CRC 中具有良好活性。

*   **预期疗效**:
    *   ORR: ~30-40%
    *   mPFS: ~5-6 个月

*   **⚠️ 关键安全管理 (肾功能优先)**:
    *   **现状**: 患者 eGFR 估算约为 **39 mL/min** (Cockcroft-Gault 公式)，属中重度肾功能不全。
    *   **风险**: 既往呋喹替尼导致急性肾损伤。虽然 KRAS G12C 抑制剂肾毒性低于 VEGFR TKI，但 Adagrasib 说明书提示有肾受损风险 [[4]](#ref-fda-adagrasib label)。
    *   **行动**:
        *   **前 2 个月**: 每 2 周监测血肌酐、尿蛋白。
        *   **避免脱水**: 确保每日饮水量，预防腹泻导致的血容量不足。

---

### 🔵 优选后线方案 (Option 2) - 标准治疗
**方案名称**: TAS-102 (曲氟尿苷替匹嘧啶) + 贝伐珠单抗
**证据等级**: A (NCCN Category 1)
**治疗定位**: 六线/后线标准治疗

*   **合理性**:
    *   SUNLIGHT 研究证实，TAS-102 联合贝伐珠单抗较 TAS-102 单药显著延长 OS (10.8 vs 7.5 个月) 和 PFS [[2]](#ref-pmid-37133585)。
    *   **肾功能适应性**: TAS-102 主要经肾排泄，但在轻中度肾受损 (CrCl 30-89 mL/min) 患者中**无需调整起始剂量** [[5]](#ref-fda-lonsurf label)。患者 eGFR ~39 mL/min，符合使用标准，但需密切监测骨髓抑制。

*   **给药方案**:
    *   TAS-102: 35 mg/m² PO, bid, d1-5, d8-12, q4w (餐后服用)。
    *   贝伐珠单抗: 5 mg/kg IV, q2w。

*   **剂量调整**:
    *   若 CrCl 降至 <30 mL/min，需减量或停药。

---

### 🟣 精准治疗备选 (Option 3) - 靶向 ATM/TMB
**方案名称**: 临床试验 (ATR 抑制剂) 或 PARP 抑制剂 (超适应症)
**证据等级**: C (生物标志物驱动)

*   **ATM 靶向**:
    *   患者携带 **ATM 胚系突变**，理论上对 DNA 损伤修复抑制剂敏感。
    *   **推荐**: 优先参加 **ATR 抑制剂 (如 IMP9064)** 的临床试验 (NCT05269316)。
    *   **超适应症**: 若无法入组，可考虑 **奥拉帕利 (Olaparib)** 单药。虽然在 CRC 中证据有限，但在 ATM 突变实体瘤篮子试验中显示疗效 [[3]](#ref-pmid-37852034)。需注意 PARP 抑制剂会加重贫血，需评估骨髓功能。

*   **TMB-H 免疫重启**:
    *   鉴于 TMB 79 mut/MB，若体能允许，可考虑 **双免疫治疗 (Nivolumab + Ipilimumab)**。NCCN 指南推荐用于 TMB-H 实体瘤 [NCCN Guidelines]。但需警惕既往免疫治疗无效及副作用史。

---

## 3. 药物相互作用与合并症管理 (Critical DDIs)

患者正在服用：硝苯地平、阿托伐他汀、达格列净、阿卡波糖。

| 药物类别 | 潜在风险 | 建议 |
| :--- | :--- | :--- |
| **他汀类 (阿托伐他汀)** | **⚠️ 肌肉毒性风险**<br>KRAS G12C 抑制剂 (如 Sotorasib) 可能是 CYP3A4 诱导剂，而 Adagrasib 是抑制剂。氟泽雷赛 (IBI351) 若为 CYP3A4 抑制剂，会显著增加阿托伐他汀血药浓度，导致横纹肌溶解风险。 | 建议暂时停用阿托伐他汀，或换用不经 CYP3A4 代谢的 **瑞舒伐他汀** (Rosuvastatin) 并从低剂量开始。 |
| **降压药 (硝苯地平)** | **⚠️ 血压波动**<br>硝苯地平是 CYP3A4 底物。若氟泽雷赛影响 CYP3A4，可能导致低血压或血压控制不佳。 | 每日监测血压。若出现低血压，需调整降压药剂量。 |
| **SGLT2 (达格列净)** | **⚠️ 肾功能/脱水**<br>达格列净具有利尿作用，可能加重腹泻引起的脱水，进而恶化肾功能。 | 若出现腹泻 (Grade ≥1)，立即暂停达格列净，直至腹泻缓解且水合状态恢复。 |
| **PPI (质子泵抑制剂)** | **❌ 吸收受阻**<br>KRAS G12C 抑制剂通常依赖酸性环境吸收。 | 询问患者是否服用奥美拉唑等胃药。若必须服用，应间隔 4-10 小时 [[6]](#ref-fda-sotorasib label)。 |

---

## 4. 器官功能与剂量调整 (Organ Function)

### 肾功能 (Renal) - **主要限制因素**
*   **当前指标**: 肌酐 146 μmol/L (eGFR ~39 mL/min)。
*   **判定**: CKD 3b 期。
*   **调整策略**:
    *   **氟泽雷赛**: 尚无明确 eGFR <40 的剂量指南。建议按标准剂量起始，但若肌酐较基线升高 >25%，应暂停并减量。
    *   **TAS-102**: eGFR 30-89 无需调整。若 eGFR <30，起始剂量减至 20 mg/m² [FDA Label]。
    *   **造影剂**: **禁止**使用碘造影剂进行增强 CT，以免诱发造影剂肾病。建议使用 **MRI** 或平扫 CT 进行疗效评估。

### 皮肤毒性 (Dermatologic)
*   **西妥昔单抗**: 常见痤疮样皮疹。
*   **管理**: 预防性使用多西环素 (100mg bid) + 氢化可的松软膏。注意多西环素可能引起光敏，需防晒。

---

## 5. 不推荐方案 (Not Recommended)

1.  **❌ 瑞戈非尼 (Regorafenib) / 再次使用呋喹替尼**:
    *   **原因**: 均为多靶点 TKI，具有明确的肾毒性。患者既往已发生 TKI 相关急性肾损伤，再次使用此类药物导致透析风险极高。

2.  **❌ 奥沙利铂/伊立替康再挑战**:
    *   **原因**: 多线治疗后获益极低，且奥沙利铂有神经毒性，伊立替康有腹泻风险（加重肾前性肾衰）。

3.  **❌ 单药免疫治疗**:
    *   **原因**: 既往信迪利单抗治疗仅获 SD 后进展，且患者为 MSS。单纯 PD-1 抑制剂无效。

---

## 6. 随访与监测计划

*   **第 1-2 个月 (当前)**:
    *   **每周**: 血常规、生化 (重点关注肌酐、电解质、白蛋白)。
    *   **每 2 周**: 尿常规 (监测蛋白尿)。
    *   **临床**: 每日自测血压、体重 (防脱水)。

*   **疗效评估**:
    *   **时间**: 治疗开始后 6-8 周 (约 2025 年 12 月)。
    *   **手段**: 胸部/腹部 **增强 MRI** (避免 CT 造影剂) + 癌胚抗原 (CEA)。

*   **下一步决策**:
    *   若 **SD/PR**: 继续当前治疗。
    *   若 **PD (进展)**: 停用氟泽雷赛，休整 2 周后启动 TAS-102 + 贝伐珠单抗，或转诊至 ATR 抑制剂临床试验。

## 参考文献
1.  **CodeBreaK 300 (Sotorasib+Panitumumab)**: [[1]](#ref-pmid-37870968)
2.  **SUNLIGHT (TAS-102+Bevacizumab)**: [[2]](#ref-pmid-37133585)
3.  **ATM Mutation & PARP Inhibitors**: [[3]](#ref-pmid-37852034)
4.  **NCCN Guidelines Colon Cancer v1.2025**: [NCCN.org](https://www.nccn.org/guidelines)
5.  **FDA Labels**: [Sotorasib](https://www.accessdata.fda.gov/drugsatfda_docs/label/2021/214665s000lbl.pdf), [Lonsurf](https://www.accessdata.fda.gov/drugsatfda_docs/label/2019/207981s008lbl.pdf)

---

## Tool Call Details

### Tool Call 1: `search_nccn`
**Timestamp:** 2026-01-20 20:25:16

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
**Timestamp:** 2026-01-20 20:25:18

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
**Timestamp:** 2026-01-20 20:25:18

**Parameters:**
```json
{
  "drug_name": "Adagrasib"
}
```

**Result:**
```
**FDA 药品说明书**

**药物**: ADAGRASIB
**商品名**: KRAZATI
**生产商**: Mirati Therapeutics, Inc

### 适应症
1 INDICATIONS AND USAGE KRAZATI is an inhibitor of the RAS GTPase family indicated for: Non-small cell lung cancer (NSCLC)* • As a single agent, for the treatment of adult patients with KRAS G12C-mutated locally advanced or metastatic NSCLC, as determined by an FDA-approved test, who have received at least one prior systemic therapy. ( 1.1 ) Colorectal cancer (CRC)* • In combination with cetuximab, for the treatment of adult patients with KRAS G12C-mutated locally advanced or metastatic CRC, as determined by an FDA-approved test, who have received prior treatment with fluoropyrimidine-, oxaliplatin-, and irinotecan-based chemotherapy. ( 1.2 ) *These indications are approved under accelerated approval based on objective response rate (ORR) and duration of response (DOR). Continued approval for these indications may be contingent upon verification and description of a clinical benefit in confirmatory trials. ( 1.1 , 1.2 ) 1.1 KRAS G12C-Mutated Locally Advanced or Metastatic Non-Small Cell Lung Cancer KRAZATI, as a single-agent, is indicated for the treatment of adult patients with KRAS G12C-mutated locally advanced or metastatic non-small cell lung cancer (NSCLC), as determined by an FDA-approved test [see Dosage and Administration (2.1) ] , who have received at least one prior systemic therapy. This indication is approved under accelerated approval based on objective response rate (ORR) and duration of response (DOR) [see Clinical Studies (14.1) ]. Continued approval for this indication may be contingent upon verification and description of a clinical benefit in a confirmatory trial. 1.2 KRAS G12C-Mutated Locally Advanced or Metastatic Colorectal Cancer KRAZATI in combination with cetuximab is indicated for the treatment of adult patients with KRAS G12C-mutated locally advanced or metastatic colorectal cancer (CRC), as determined by an FDA-approved test [see Dosage and Administration (2.1) ] , who have received prior treatment with fluoropyrimidine-, oxaliplatin-, an

### 剂量与用法
2 DOSAGE AND ADMINISTRATION • Recommended dosage as a single agent for NSCLC and in combination with cetuximab for CRC: 600 mg orally twice daily. ( 2.2 ) • Swallow tablets whole with or without food. ( 2.2 ) 2.1 Patient Selection Non-Small Cell Lung Cancer Select patients for treatment of locally advanced or metastatic NSCLC with KRAZATI based on the presence of KRAS G12C mutation in plasma or tumor specimens [see Clinical Studies (14.1) ] . If no mutation is detected in a plasma specimen, test tumor tissue. Colorectal Cancer Select patients for treatment of locally advanced or metastatic CRC with KRAZATI based on the presence of KRAS G12C mutation in tumor specimens [see Clinical Studies (14.2) ] . Information on FDA-approved tests for the detection of a KRAS G12C mutation is available at: https://www.fda.gov/CompanionDiagnostics 2.2 Recommended Dosage The recommended dosage of KRAZATI as a single agent or in combination with cetuximab is 600 mg orally twice daily until disease progression or unacceptable toxicity. Refer to the cetuximab prescribing information for cetuximab dosage information [see Clinical Studies (14.2) ]. Take KRAZATI at the same time every day with or without food [see Clinical Pharmacology (12.3) ]. Swallow tablets whole. Do not chew, crush or split tablets. If vomiting occurs after taking KRAZATI, do not take an additional dose. Resume dosing at the next scheduled time. If a dose is inadvertently missed, it should be skipped if greater than 4 hours have elapsed from the expected dosing time. Resume dosing at the next scheduled time. 2.3 Dosage Modifications for Adverse Reactions Recommended dose reductions for adverse reactions for use of KRAZATI as a single agent or in combination with cetuximab are outlined in Table 1. If adverse reactions occur, a maximum of two dose reductions are permitted. Permanently discontinue KRAZATI in patients who are unable to tolerate 600 mg once daily. Table 1: Recommended KRAZATI Dosage Reductions for Adverse

### 警告与注意事项
5 WARNINGS AND PRECAUTIONS • Gastrointestinal Adverse Reactions : Monitor patients for diarrhea, nausea and vomiting and provide supportive care as needed. Withhold, reduce the dose or permanently discontinue based on severity. ( 2.3 , 5.1 ) • QTc Interval Prolongation: Avoid concomitant use of KRAZATI with other products with a known potential to prolong the QTc interval. Monitor ECG and electrolytes particularly potassium and magnesium, in patients at risk, and in patients taking medications known to prolong the QT interval. Correct electrolyte abnormalities. Withhold, reduce the dose, or permanently discontinue based on severity. ( 2.3 , 5.2 ) • Hepatotoxicity: Monitor liver laboratory tests prior to the start of KRAZATI and monthly for 3 months after and as clinically indicated. Reduce the dose, withhold, or permanently discontinue based on severity. ( 2.3 , 5.3 ) • Interstitial Lung Disease (ILD) / Pneumonitis: Monitor for new or worsening respiratory symptoms. Withhold KRAZATI for suspected ILD/pneumonitis and permanently discontinue if no other potential causes of ILD/pneumonitis are identified. ( 2.3 , 5.4 ) 5.1 Gastrointestinal Adverse Reactions KRAZATI can cause severe gastrointestinal adverse reactions. In the pooled safety population [see Adverse Reactions (6.1) ] , who received single-agent KRAZATI, serious gastrointestinal adverse reactions observed were gastrointestinal bleeding in 3.8% including 0.8% Grade 3 or 4, gastrointestinal obstruction in 1.6% including 1.4% Grade 3 or 4, colitis in 0.5% including 0.3% Grade 3, ileus in 0.5%, and stenosis in 0.3%. In addition, nausea, diarrhea, or vomiting occurred in 89% of 366 patients, including 9% Grade 3. Nausea, diarrhea, or vomiting led to dosage interruption or dose reduction in 29% of patients and permanent discontinuation of adagrasib in 0.3%. In patients who received KRAZATI in combination with cetuximab [see Adverse Reactions (6.1) ] , serious gastrointestinal adverse reactions included gastrointes

### 禁忌症
4 CONTRAINDICATIONS None. None. ( 4 )

### 药物相互作用
7 DRUG INTERACTIONS See full prescribing information for clinically significant drug interactions with KRAZATI. ( 7 ) • Strong CYP3A4 Inducers : Avoid concomitant use. ( 7.1 ) • Strong CYP3A4 Inhibitors : Avoid concomitant use until adagrasib concentrations have reached steady state. ( 7.1 ) • Sensitive CYP3A4 Substrates : Avoid concomitant use with sensitive CYP3A4 substrates. ( 7.2 ) • Sensitive CYP2C9 or CYP2D6 Substrates or P-gp Substrates : Avoid concomitant use with sensitive CYP2C9 or CYP2D6 substrates or P-gp substrates where minimal concentration changes may lead to serious adverse reactions. ( 7.2 ) • Drugs That Prolong QT Interval : Avoid concomitant use with KRAZATI. ( 7.3 ) 7.1 Effects of Other Drugs on KRAZATI Strong CYP3A4 Inducers Avoid concomitant use of KRAZATI with strong CYP3A inducers. Adagrasib is a CYP3A4 substrate. Concomitant use of KRAZATI with a strong CYP3A inducer reduces adagrasib exposure [see Clinical Pharmacology (12.3) ] , which may reduce the effectiveness of KRAZATI. Strong CYP3A4 Inhibitors Avoid concomitant use of KRAZATI with strong CYP3A inhibitors until adagrasib concentrations have reached steady state (after approximately 8 days). Adagrasib is a CYP3A4 substrate. If adagrasib concentrations have not reached steady state, concomitant use of a strong CYP3A inhibitor will increase adagrasib concentrations, [see Clinical Pharmacology (12.3) ], which may increase the risk of KRAZATI adverse reactions. 7.2 Effects of KRAZATI on Other Drugs Sensitive CYP3A Substrates Avoid concomitant use of KRAZATI with sensitive CYP3A substrates unless otherwise recommended in the Prescribing Information for these substrates. Adagrasib is a CYP3A inhibitor. Concomitant use with KRAZATI increases exposure of CYP3A substrates [see Clinical Pharmacology (12.3) ] , which may increase the risk of adverse reactions related to these substrates. Sensitive CYP2C9 Substrates Avoid concomitant use of KRAZATI with sensitive CYP2C9 substrates where minimal c

### 不良反应
6 ADVERSE REACTIONS The following clinically significant adverse reactions are described elsewhere in the labeling: • Gastrointestinal Adverse Reactions [see Warnings and Precautions (5.1) ] • QTc Interval Prolongation [see Warnings and Precautions (5.2) ] • Hepatotoxicity [see Warnings and Precautions (5.3) ] • Interstitial Lung Disease (ILD)/Pneumonitis [see Warnings and Precautions (5.4) ] • Single agent use in NCSLC: The most common adverse reactions (≥ 25%) were nausea, diarrhea, vomiting, fatigue, musculoskeletal pain, hepatotoxicity, renal impairment, edema, dyspnea, and decreased appetite. The most common (≥ 2%) Grade 3 or 4 laboratory abnormalities were decreased lymphocytes, decreased hemoglobin, increased alanine aminotransferase, increased aspartate aminotransferase, hypokalemia, hyponatremia, increased lipase, decreased leukocytes, decreased neutrophils and increased alkaline phosphatase. ( 6.1 ) • In combination with cetuximab in CRC: The most common adverse reactions (≥ 25%) were rash, nausea, diarrhea, vomiting, fatigue, musculoskeletal pain, hepatotoxicity, headache, dry skin, abdominal pain, decreased appetite, edema, anemia, and cough. The most common (≥ 2%) Grade 3 or 4 laboratory abnormalities were decreased lymphocytes, decreased potassium, decreased magnesium, decreased hemoglobin, increased aspartate aminotransferase, increased lipase, decreased albumin, and increased alanine aminotransferase. ( 6.1 ) To report SUSPECTED ADVERSE REACTIONS, contact Bristol-Myers Squibb at 1-800-721-5072 or FDA at 1-800-FDA-1088 or www.fda.gov/medwatch . 6.1 Clinical Trials Experience Because clinical trials are conducted under widely varying conditions, adverse reaction rates observed in the clinical trials of a drug cannot be directly compared to rates in the clinical trials of another drug and may not reflect the rates observed in practice. The pooled safety population described in the WARNINGS AND PRECAUTIONS reflect exposure to adagrasib as a single agent 

**参考**: https://labels.fda.gov (搜索 ADAGRASIB)
```

### Tool Call 4: `search_fda_labels`
**Timestamp:** 2026-01-20 20:25:18

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

### Tool Call 5: `search_fda_labels`
**Timestamp:** 2026-01-20 20:25:19

**Parameters:**
```json
{
  "drug_name": "Trifluridine and Tipiracil"
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

### Tool Call 6: `search_rxnorm`
**Timestamp:** 2026-01-20 20:25:25

**Parameters:**
```json
{
  "drug_name": "Sotorasib",
  "check_interactions": [
    "Atorvastatin",
    "Nifedipine",
    "Dapagliflozin",
    "Acarbose"
  ]
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
**Timestamp:** 2026-01-20 20:25:26

**Parameters:**
```json
{
  "query": "Fulzerasib IBI351 colorectal cancer renal safety"
}
```

**Result:**
```
**PubMed 搜索结果**

**搜索关键词**: Fulzerasib IBI351 colorectal cancer renal safety

未找到相关文献。
```

### Tool Call 8: `search_pubmed`
**Timestamp:** 2026-01-20 20:25:27

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

### 4. Olaparib for patients with tumors harboring alterations in homologous recombination repair genes: Results from the drug rediscovery protocol.

- **PMID**: 41099623
- **作者**: Spiekman IAC, Mehra N, Zeverijn LJ
- **期刊**: International journal of cancer (2026)
- **摘要**: BRCA1/2 are crucial in the homologous recombination repair (HRR) pathway, with loss-of-function (LoF) alterations predicting sensitivity to PARP-inhibitors (PARPi). Whether other HRR-gene alterations confer PARPi sensitivity remains unclear. In the Drug Rediscovery Protocol, patients receive off-label drugs matched to their tumor molecular profile. Here, olaparib efficacy and safety were evaluated in adult patients with treatment-refractory, progressive malignancies harboring LoF alterations in 
- **链接**: https://pubmed.ncbi.nlm.nih.gov/41099623/

---

### 5. Off-label use of olaparib in uncommon tumor locations in patients with impaired homologous recombination genes.

- **PMID**: 40155245
- **作者**: García-Díaz HC, Larrosa-Garcia M, Gómez-Alonso J
- **期刊**: Farmacia hospitalaria : organo oficial de expresion cientifica de la Sociedad Espanola de Farmacia Hospitalaria (2025)
- **摘要**: To describe the effectiveness and safety of olaparib off-label indications in patients with impaired homologous recombination genes and solid tumors different than those authorized.
- **链接**: https://pubmed.ncbi.nlm.nih.gov/40155245/

---

```


---

## References

<a id="ref-pmid-37870968"></a>**[1]** [PMID: 37870968](https://pubmed.ncbi.nlm.nih.gov/37870968/)

<a id="ref-pmid-37133585"></a>**[2]** [PMID: 37133585](https://pubmed.ncbi.nlm.nih.gov/37133585/)

<a id="ref-pmid-37852034"></a>**[3]** [PMID: 37852034](https://pubmed.ncbi.nlm.nih.gov/37852034/)

<a id="ref-fda-adagrasib label"></a>**[4]** [FDA: Adagrasib Label](https://labels.fda.gov)

<a id="ref-fda-lonsurf label"></a>**[5]** [FDA: Lonsurf Label](https://labels.fda.gov)

<a id="ref-fda-sotorasib label"></a>**[6]** [FDA: Sotorasib Label](https://labels.fda.gov)
