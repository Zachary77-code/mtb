# MTB Chair Final Synthesis Report

## Analysis Output

这份 MTB 报告汇总了病理科、遗传科、临床试验专员及肿瘤内科专家的意见。报告严格遵循您的格式要求，保留了所有关键细节、治疗史及临床试验推荐。

---

# 分子肿瘤专家委员会 (MTB) 综合报告

## 1. 执行摘要 (Executive Summary)

:::exec-summary
患者: 70岁男性，乙状结肠中分化腺癌，IV期 (ypT4aN2aM1)
关键分子特征: KRAS G12C (11.5%), ATM 胚系突变, TMB-High (79/Mb), MSS
当前治疗: 氟泽雷赛 + 西妥昔单抗 (2025.10 起，五线治疗)
核心建议: 继续当前双靶向方案，密切监测肾功能及药物相互作用
紧急程度: 常规
:::

**综合意见**:
患者为晚期结直肠癌，携带 **KRAS G12C** 突变及 **ATM 胚系突变**。尽管表现为 MSS (微卫星稳定)，但 **TMB 极高 (79 mut/Mb)**，提示特殊的 POLE/POLD1 样超突变表型，解释了既往免疫联合治疗曾获短暂控制。鉴于多线治疗失败且既往因呋喹替尼导致**急性肾损伤 (AKI)**，目前的 **氟泽雷赛 (KRASi) + 西妥昔单抗 (EGFRi)** 是基于机制的最佳挽救方案[[ref:R1|CodeBreaK 300|https://pubmed.ncbi.nlm.nih.gov/37870968/|Evidence B]]。后续治疗需严格规避强肾毒性药物。

---

## 2. 患者概况 (Patient Profile)

### 人口学特征
- **年龄**: 70 岁
- **性别**: 男性
- **ECOG PS**: 1 分
- **体格**: 165cm, 66kg

### 肿瘤诊断
- **原发灶**: 乙状结肠中分化腺癌
- **分期**: ypT4aN2aM1 (IV期)
- **转移部位**:
    - **当前**: 双肺多发转移 (最大 2.1×1.5cm)
    - **既往**: 肝转移 (已行根治性切除)、区域淋巴结 (5/19 阳性)
- **肿瘤标记物**: CEA 112 ng/mL (升高), CA-199 145 U/mL

### 合并症与器官功能
- **肾功能**: **受损** (肌酐 146 μmol/L, eGFR ~40-50 mL/min, CKD 3期)
- **心血管**: 高血压、心脏支架术后
- **代谢**: 糖尿病
- **既往毒性**: 呋喹替尼致急性肾损伤 (AKI)

---

## 3. 分子特征 (Molecular Profile)

### 可行动变异 (Actionable Alterations)

| 基因 | 变异 | 类型 | VAF | CIViC 等级 | 证据/药物 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **KRAS** | **G12C** | SNV | 11.5% | Level B | **氟泽雷赛+西妥昔单抗** (当前用药)<br>Sotorasib/Adagrasib+EGFRi |
| **ATM** | **胚系突变** | Germline | - | Level C | 铂类敏感 (已证实)<br>PARP 抑制剂 (奥拉帕利等) |

### 免疫生物标志物
- **MSI 状态**: **MSS** (微卫星稳定) - pMMR (MLH1/PMS2/MSH2/MSH6 均阳性)
- **TMB**: **79 mut/Mb** (超高) - 提示 POLE/POLD1 校对突变可能
- **PD-L1**: CPS = 3 (低表达)

### 阴性发现
- BRAF V600E (-), HER2 (0), NRAS (-), panTRK (-)

### 变异解读
1.  **KRAS G12C**: 结直肠癌中单药 G12C 抑制剂效果差 (ORR <20%)，需联合抗 EGFR 单抗阻断反馈回路。
2.  **TMB/MSS 矛盾**: MSS 肠癌通常 TMB<10。此患者 TMB 79 极高，虽为 MSS，但具有高免疫原性，解释了为何三线免疫联合曾有效 (SD 缩小)。
3.  **ATM 胚系**: 导致同源重组修复缺陷 (HRD)，与一线奥沙利铂疗效好 (PR) 一致。

---

## 4. 治疗史回顾 (Treatment History)

:::timeline
- line: 1线
  date: 2022.08-2022.12
  regimen: 奥沙利铂+卡培他滨+贝伐珠单抗 (5程)
  response: PR
  type: neoadjuvant
  note: 新辅助化疗，疗效显著

- line: 手术
  date: 2023.01
  regimen: 根治性手术
  response: TRG2
  type: surgery
  note: 切除原发灶+肝转移+淋巴结清扫

- line: 1线
  date: 2023.03-2023.05
  regimen: 奥沙利铂+卡培他滨 (3程)
  response: -
  type: adjuvant
  note: 术后辅助化疗

- line: 1线
  date: 2023.05-2023.08
  regimen: 卡培他滨单药
  response: -
  type: maint
  note: 维持治疗，双肺出现小结节

- line: 2线
  date: 2023.08-2024.01
  regimen: FOLFIRI (伊立替康+5-FU)+贝伐珠单抗
  response: SD
  type: pd
  note: 因CEA升高、肺结节增大换方案

- line: 2线
  date: 2024.02-2024.06
  regimen: 卡培他滨单药
  response: -
  type: maint
  note: 维持治疗

- line: 3线
  date: 2024.07
  regimen: 呋喹替尼+信迪利单抗
  response: 毒性停药
  type: event
  note: ⚠️ 严重不良反应：急性肾损伤+肢体水肿

- line: 3线
  date: 2024.09
  regimen: 雷替曲塞+信迪利单抗
  response: -
  type: event
  note: 出现发热（疑似感染）

- line: 3线
  date: 2024.10-2025.02
  regimen: 雷替曲塞+信迪利单抗
  response: SD(缩小)
  type: pd
  note: 病情暂时控制，CEA降至17.2

- line: 4线
  date: 2025.02-2025.10
  regimen: 信迪利单抗+抗肿瘤新抗原mRNA疫苗
  response: PD
  type: pd
  note: 含KRAS G12C新抗原，但肺灶增大，CEA升至112

- line: 5线(当前)
  date: 2025.10-今
  regimen: 氟泽雷赛+西妥昔单抗
  response: 待评估
  type: current
  note: 针对KRAS G12C靶向治疗
:::

**关键观察**:
- **铂类敏感**: 一线含铂方案获 PR，与 ATM 突变一致。
- **肾毒性高危**: 呋喹替尼导致急性肾损伤，限制了后续 TKI 和高剂量化疗的使用。
- **免疫获益有限**: 尽管 TMB 高，但免疫联合治疗仅获 SD，疫苗治疗 PD，提示免疫逃逸。

---

## 5. 药物/方案对比 (Regimen Comparison)

| 方案 | 证据等级 | 预期 ORR | 预期 mPFS | 关键毒性 | 适用性分析 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **氟泽雷赛 + 西妥昔单抗** | **B (推荐)** | ~30-46% | ~6-7月 | 皮疹、腹泻、低镁 | **当前最佳**。针对驱动基因，且避开了强肾毒性。 |
| **TAS-102 + 贝伐珠单抗** | **A (标准)** | ~6% | 5.6月 | 骨髓抑制 | **备选**。需根据肾功能调整剂量 (CrCl <30需减量)。 |
| **Glecirasib + SHP2i** | **C (试验)** | 未知 | 未知 | 肝毒性、水肿 | **耐药后首选**。针对 G12C 耐药机制。 |
| **呋喹替尼** | **A (禁忌)** | ~4% | 3.7月 | **肾损伤**、高血压 | **绝对禁忌**。既往已发生严重 AKI。 |

**对比总结**:
当前双靶向方案（KRASi+EGFRi）在有效率上显著优于标准三线治疗（TAS-102）。考虑到患者肾功能不全，应优先选择主要经肝代谢的靶向药物，避免加重肾脏负担。

---

## 6. 器官功能与剂量 (Organ Function & Dosing)

### 肾功能管理 (核心瓶颈)
- **现状**: 肌酐 146 μmol/L，eGFR 40-50 mL/min (CKD 3a期)。
- **风险**: 既往药物性 AKI 病史，肾脏储备差。

### 剂量调整建议
1.  **氟泽雷赛 (Fulzerasib)**:
    - 主要经肝代谢。eGFR >30 mL/min 通常**无需调整剂量**。
    - ⚠️ **药物相互作用**: 氟泽雷赛可能诱导 CYP3A4，降低**硝苯地平**和**阿托伐他汀**疗效。需密切监测血压和血脂，必要时换药。
2.  **西妥昔单抗 (Cetuximab)**:
    - 无需根据肾功能调整。
    - ⚠️ **低镁血症**: 需每次输注前监测血镁，防止电解质紊乱诱发心脏事件。
3.  **TAS-102 (若后续使用)**:
    - 若 CrCl 降至 <30 mL/min，起始剂量需减至 20 mg/m²。目前水平可全量，但需严密监测中性粒细胞。

---

## 7. 治疗路线图 (Treatment Roadmap)

:::roadmap
- title: 当前方案 (五线)
  status: current
  regimen: 氟泽雷赛 + 西妥昔单抗
  actions:
    - 每2周监测肝肾功能
    - 关注皮疹与腹泻
    - 监测血压 (药物相互作用)

- title: 若有效 (PR/SD)
  status: success
  regimen: 维持治疗
  actions:
    - 直至疾病进展或毒性不耐受
    - 考虑对残留肺结节行 SBRT (若寡进展)

- title: 若进展 (PD)
  status: danger
  regimen: 临床试验 / TAS-102
  actions:
    - 首选: NCT05288205 (Glecirasib + SHP2i)
    - 备选: TAS-102 + 贝伐珠单抗 (注意肾功能)
    - 液体活检寻找耐药机制
:::

---

## 8. 分子复查建议 (Re-biopsy)

**时机**: 当前治疗 (KRASi+EGFRi) 进展时。
**方式**: **液体活检 (ctDNA)** 优选（因肺转移灶取样有风险）。
**目的**:
1.  **KRAS 继发突变**: 检测 Y96D、G12D/V 等阻碍药物结合的突变。
2.  **旁路激活**: 检测 MET 扩增（针对性使用 MET 抑制剂）或 BRAF/MAP2K1 突变。
3.  **ATM 状态**: 确认 ATM 突变是否仍为主克隆，评估 PARP 抑制剂可行性。

---

## 9. 临床试验推荐 (Clinical Trials)

根据 Recruiter 报告，以下试验为优先推荐（需核实肾功能入组标准）：

### 推荐一：克服 KRAS G12C 耐药
#### Trial 1: [NCT05288205] - Glecirasib (JAB-21822) 联合 JAB-3312 (SHP2i)
- **阶段**: Phase I/II
- **药物**: Glecirasib (KRAS G12Ci) + JAB-3312 (SHP2抑制剂)
- **靶点**: KRAS G12C, SHP2
- **状态**: 招募中
- **中心**: 北京协和医院、中国医学科学院肿瘤医院等
- **理由**: SHP2 抑制剂可阻断 KRAS 通路的反馈性激活，是克服 G12C 抑制剂耐药的最强策略。
- **注意**: 需确认 CrCl 40-50 mL/min 是否符合入组条件。

### 推荐二：新型 ADC 药物
#### Trial 2: [NCT05489211] - TROPION-PanTumor03 (Dato-DXd)
- **阶段**: Phase II
- **药物**: Datopotamab Deruxtecan (TROP2 ADC)
- **靶点**: TROP2
- **状态**: 招募中
- **中心**: 广州、重庆、杭州等多地
- **理由**: TROP2 在肠癌高表达，ADC 药物机制不同于 TKI，适合多线耐药患者。通常肾功能要求较宽 (CrCl ≥30)。

### 推荐三：标准治疗改良
#### Trial 3: [NCT06764680] - TAS-102 联合 贝伐珠单抗/信迪利单抗
- **阶段**: Phase II
- **药物**: TAS-102 + 贝伐珠单抗
- **状态**: 招募中
- **中心**: 中山大学肿瘤防治中心
- **理由**: 标准三线疗法的优化版。建议选择联合贝伐珠单抗组（因免疫既往已耐药）。

### 探索性推荐
#### Trial 4: PARP 抑制剂篮子试验
- **理由**: 基于 **ATM 胚系突变**。可关注奥拉帕利或尼拉帕利在同源重组修复缺陷 (HRD) 实体瘤中的试验。

---

## 10. 局部治疗建议 (Local Therapy)

**当前状态**: 双肺多发转移，最大 2.1cm。
**建议**:
1.  **暂不干预**: 目前为全身系统性疾病，且正在接受新药治疗，以药物控制为主。
2.  **寡进展处理**: 若全身病灶稳定，仅个别肺结节增大，可考虑 **SBRT (立体定向放疗)**，剂量建议 48-60 Gy / 3-5 F。
3.  **骨转移监测**: 病历提及既往淋巴结清扫含“骨/肝转移”，需核实当前是否有骨破坏。若有骨痛，可予姑息放疗 (30 Gy/10F)。

---

## 11. 核心建议汇总 (Core Recommendations)

### 推荐治疗方案
1.  **即刻执行**: **氟泽雷赛 (600mg BID) + 西妥昔单抗 (500mg/m² q2w)** [[Evidence B]]
    - **理由**: 针对 KRAS G12C/EGFR 反馈回路的机制性联合，疗效优于单药。
    - **预期**: ORR ~30%，PFS ~6个月。

2.  **支持治疗**:
    - **皮肤管理**: 预防性使用保湿霜和多西环素（针对西妥昔单抗皮疹）。
    - **血压监测**: 每日监测，若血压升高及时调整降压药（避开硝苯地平，改用缬沙坦等）。
    - **肾脏保护**: 避免使用 NSAIDs（布洛芬等），造影剂检查需水化。

3.  **监测计划**:
    - 每 2 周查血常规、肝肾功能、电解质（镁）。
    - 每 6-8 周行 CT 评估疗效。

### 不建议 (Not Recommended)
1.  ❌ **呋喹替尼 (Fruquintinib)**: **绝对禁忌**。既往导致严重 AKI，再次使用极高风险导致透析依赖。
2.  ❌ **PD-1 单药**: 尽管 TMB 高，但患者为 MSS 且既往免疫联合治疗 PD，单药无效 [[Evidence A]]。
3.  ❌ **顺铂/高剂量甲氨蝶呤**: 肾毒性大，禁用于 eGFR < 60 患者。

---

## 12. 参考文献 (References)

1.  [PMID: 37870968 - CodeBreaK 300: Sotorasib plus Panitumumab in Refractory Colorectal Cancer](https://pubmed.ncbi.nlm.nih.gov/37870968/)
2.  [PMID: 40715048 - Fulzerasib (IBI351) Phase I/II Study](https://pubmed.ncbi.nlm.nih.gov/40715048/)
3.  [PMID: 37142616 - SUNLIGHT: Trifluridine/tipiracil plus bevacizumab for third-line treatment](https://pubmed.ncbi.nlm.nih.gov/37142616/)
4.  [NCT05288205 - Glecirasib + SHP2i Clinical Trial](https://clinicaltrials.gov/study/NCT05288205)
5.  [NCT05489211 - TROPION-PanTumor03](https://clinicaltrials.gov/study/NCT05489211)
6.  [NCCN Guidelines for Colon Cancer v1.2025](https://www.nccn.org/guidelines)
7.  [PMID: 41424250 - ATM deficiency and PARP inhibitors](https://pubmed.ncbi.nlm.nih.gov/41424250/)