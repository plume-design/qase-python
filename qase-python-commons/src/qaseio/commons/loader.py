from __future__ import annotations

import certifi
import itertools

from qaseio.api_client import ApiClient
from qaseio.configuration import Configuration
from qaseio.api.plans_api import PlansApi
from qaseio.rest import ApiException
from qaseio.utils.result import Result
from qaseio.utils.run import Run


class TestOpsPlanLoader:
    def __init__(self, api_token, host="qase.io"):
        configuration = Configuration()
        configuration.api_key["TokenAuth"] = api_token
        configuration.host = f"https://api.{host}/v1"

        self.client = ApiClient(configuration)
        self.case_list = []

        configuration.ssl_ca_cert = certifi.where()

    def load(self, code: str, plan_id: int | None, run_id: str | None, rerun: list[str]) -> list:
        # if run_id is specified check first if there are tests, if they are, ignore plan_id and use cases from there
        # if run_id is empty, get all cases from plan_id (Jenkins plugin)
        if rerun and run_id is None:
            raise EnvironmentError("RUN ID needs to be specified for rerun")
        test_run_cases = []
        if run_id:
            test_run_cases = self._get_cases_from_test_run(code, int(run_id), rerun)

        # use test run_if first
        if test_run_cases:
            self.case_list = test_run_cases
        # if run was empty or fully completed in case of rerun use cases from the test plan_id
        elif rerun is False and plan_id:
            self.case_list = self._get_cases_from_test_plan(code, int(plan_id))
        # nothing to do
        else:
            self.case_list = []
        print(f"[Qase]  {len(self.case_list)} cases selected: {self.case_list}\n")
        return self.case_list

    def _get_cases_from_test_plan(self, code: str, plan_id: int):
        print(f"[Qase] Getting {code} tests cases from test plan: {plan_id}")
        api_instance = PlansApi(self.client)
        try:
            response = api_instance.get_plan(code=code, id=plan_id)
            if hasattr(response, "result"):
                return [c.case_id for c in response.result.cases]
            raise ValueError("Unable to find given plan")
        except ApiException as e:
            print("Unable to load test plan data: %s\n" % e)
        return []

    def _get_cases_from_test_run(self, code: str, run_id: int, rerun: list[str]):
        print(f"[Qase] Getting {code} test cases from run {run_id}: {rerun=}")
        run_cases = []
        try:
            run_cases = Run(project=code, run_id=run_id).get_cases()
        except ApiException as e:
            print("Unable to load test run data: %s\n" % e)
        if not run_cases:
            return []
        if not rerun:
            return run_cases
        rerun_cases = []
        run_results = Result(project=code, run_id=run_id).get_results()
        run_results.sort(key=lambda result: result["status"])
        cases_by_status = {
            status: [result["case_id"] for result in results]
            for status, results in itertools.groupby(run_results, key=lambda result: result["status"])
        }
        for status in rerun:
            if status == "untested":
                already_ran = {result["case_id"] for result in run_results if result["status"] != "untested"}
                ids = [case_id for case_id in run_cases if case_id not in already_ran]
            else:
                ids = cases_by_status.get(status, [])
            if ids:
                print(f"[Qase] Adding {len(ids)} {status.upper()} test cases from run {run_id}: {ids}")
            rerun_cases.extend(ids)
        print(f"[Qase] Final number of test cases from run {run_id} to start: {len(rerun_cases)}")
        return rerun_cases
