"""
ClinicalTrials.gov API v2 客户端

API 文档: https://clinicaltrials.gov/data-api/api
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, List, Any, Optional
from src.utils.logger import mtb_logger as logger


class ClinicalTrialsClient:
    """ClinicalTrials.gov API v2 客户端"""

    BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "MTB-Workflow/1.0"
        })
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def search_trials(
        self,
        condition: str,
        intervention: str = None,
        location: str = "China",
        status: str = "RECRUITING",
        max_results: int = 20
    ) -> List[Dict]:
        """
        搜索临床试验

        Args:
            condition: 疾病/条件 (如 "NSCLC", "EGFR mutation lung cancer")
            intervention: 干预措施/药物 (可选)
            location: 地点 (默认中国)
            status: 试验状态 (RECRUITING, NOT_YET_RECRUITING, COMPLETED 等)
            max_results: 最大结果数

        Returns:
            试验列表 [{nct_id, title, phase, status, conditions, interventions, locations, sponsors}]
        """
        # 构建查询参数
        params = {
            "format": "json",
            "pageSize": max_results,
            "query.cond": condition,
            "filter.overallStatus": status,
        }

        if intervention:
            params["query.intr"] = intervention

        if location:
            params["query.locn"] = location

        # 请求的字段
        params["fields"] = ",".join([
            "NCTId",
            "BriefTitle",
            "OfficialTitle",
            "Phase",
            "OverallStatus",
            "Condition",
            "InterventionName",
            "InterventionType",
            "LocationFacility",
            "LocationCity",
            "LocationCountry",
            "LeadSponsorName",
            "EnrollmentCount",
            "StartDate",
            "PrimaryCompletionDate",
            "EligibilityCriteria"
        ])

        try:
            logger.debug(f"[CT.gov] 搜索: {condition}, 干预: {intervention}, 地点: {location}")
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            studies = data.get("studies", [])
            if not studies:
                logger.info(f"[CT.gov] 无匹配试验: {condition}")
                return []

            logger.debug(f"[CT.gov] 找到 {len(studies)} 项试验")
            return self._parse_studies(studies)

        except Exception as e:
            logger.error(f"[CT.gov] 搜索失败: {e}")
            return []

    def _parse_studies(self, studies: List[Dict]) -> List[Dict]:
        """解析试验数据"""
        results = []

        for study in studies:
            protocol = study.get("protocolSection", {})

            # 基本信息
            id_module = protocol.get("identificationModule", {})
            nct_id = id_module.get("nctId", "")
            brief_title = id_module.get("briefTitle", "")
            official_title = id_module.get("officialTitle", "")

            # 状态
            status_module = protocol.get("statusModule", {})
            overall_status = status_module.get("overallStatus", "")
            start_date = status_module.get("startDateStruct", {}).get("date", "")
            completion_date = status_module.get("primaryCompletionDateStruct", {}).get("date", "")

            # 设计
            design_module = protocol.get("designModule", {})
            phases = design_module.get("phases", [])
            phase = ", ".join(phases) if phases else "N/A"
            enrollment = design_module.get("enrollmentInfo", {}).get("count", 0)

            # 条件
            conditions_module = protocol.get("conditionsModule", {})
            conditions = conditions_module.get("conditions", [])

            # 干预
            interventions = []
            arms_module = protocol.get("armsInterventionsModule", {})
            for intr in arms_module.get("interventions", []):
                interventions.append({
                    "name": intr.get("name", ""),
                    "type": intr.get("type", "")
                })

            # 地点 (只取中国的)
            locations = []
            locations_module = protocol.get("contactsLocationsModule", {})
            for loc in locations_module.get("locations", []):
                if loc.get("country") == "China":
                    locations.append({
                        "facility": loc.get("facility", ""),
                        "city": loc.get("city", "")
                    })

            # 资助方
            sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
            lead_sponsor = sponsor_module.get("leadSponsor", {}).get("name", "")

            # 入选标准
            eligibility_module = protocol.get("eligibilityModule", {})
            eligibility_criteria = eligibility_module.get("eligibilityCriteria", "")

            results.append({
                "nct_id": nct_id,
                "brief_title": brief_title,
                "official_title": official_title,
                "phase": phase,
                "status": overall_status,
                "enrollment": enrollment,
                "start_date": start_date,
                "completion_date": completion_date,
                "conditions": conditions,
                "interventions": interventions,
                "locations": locations,  # 返回完整地点列表
                "sponsor": lead_sponsor,
                "eligibility_criteria": eligibility_criteria,  # 返回完整入选标准
                "url": f"https://clinicaltrials.gov/study/{nct_id}"
            })

        return results

    def get_trial_details(self, nct_id: str) -> Optional[Dict]:
        """
        获取单个试验的详细信息

        Args:
            nct_id: 试验 NCT 编号 (如 NCT04532463)

        Returns:
            试验详细信息
        """
        url = f"{self.BASE_URL}/{nct_id}"
        params = {"format": "json"}

        try:
            logger.debug(f"[CT.gov] 获取试验详情: {nct_id}")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            studies = self._parse_studies([data])
            return studies[0] if studies else None

        except Exception as e:
            logger.error(f"[CT.gov] 获取 {nct_id} 失败: {e}")
            return None


if __name__ == "__main__":
    # 测试
    client = ClinicalTrialsClient()

    print("=== 搜索 EGFR 突变 NSCLC 试验 (中国招募中) ===")
    trials = client.search_trials(
        condition="EGFR mutation non-small cell lung cancer",
        intervention="osimertinib",
        location="China",
        status="RECRUITING",
        max_results=3
    )

    for t in trials:
        print(f"\n- {t['nct_id']}: {t['brief_title'][:60]}...")
        print(f"  Phase: {t['phase']}, 状态: {t['status']}")
        print(f"  干预: {[i['name'] for i in t['interventions']]}")
        print(f"  中国中心: {[l['facility'] for l in t['locations']][:3]}")
