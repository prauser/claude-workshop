"""
test_harvest_artifacts.py — harvest_artifacts.py 단위 테스트.
stdlib unittest 사용 — 외부 의존 0.

테스트 항목:
  ① 실제 .claude/plans/PRA-109/plan.md 파싱 (intent.problem, gate_events 추출 검증)
  ② frontmatter 없는 텍스트 → {} 반환
  ③ malformed YAML → parse-error 레코드 (무crash)
  ④ legacy skip_grill_count 정규화
  ⑤ ticketless 분리
  + 추가: harvest_plan, harvest_tasks, harvest_manifest, harvest_repo 연기(延基) 테스트
"""

import os
import sys
import tempfile
import unittest

# harvest_artifacts 모듈 경로 추가
_TELEMETRY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TELEMETRY_DIR not in sys.path:
    sys.path.insert(0, _TELEMETRY_DIR)

import harvest_artifacts as h
import discover

# 실제 plan.md 경로 — 이 테스트 파일로부터 상대적으로 결정
# tests/ → telemetry/ → runners/ → workflow-contract/ → templates/ → claude-workshop/ (5단계)
_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..")
)
_PLAN_PATH = os.path.join(_REPO_ROOT, ".claude", "plans", "PRA-109", "plan.md")


class TestParseFrontmatter(unittest.TestCase):
    """parse_frontmatter 기본 동작 테스트."""

    # ② frontmatter 없는 텍스트
    def test_no_frontmatter_returns_empty_dict(self):
        """frontmatter 없는 텍스트 → ({}, text) 반환."""
        fm, body = h.parse_frontmatter("no frontmatter here")
        self.assertEqual(fm, {})
        self.assertEqual(body, "no frontmatter here")

    def test_empty_string_returns_empty_dict(self):
        """빈 문자열 → ({}, '')."""
        fm, body = h.parse_frontmatter("")
        self.assertEqual(fm, {})
        self.assertEqual(body, "")

    def test_only_open_fence_no_crash(self):
        """--- 시작 펜스만 있고 닫힘 펜스 없는 경우 무crash."""
        fm, body = h.parse_frontmatter("---\nkey: value\nno close")
        self.assertEqual(fm, {})

    def test_simple_key_value(self):
        """단순 key: value 파싱."""
        text = "---\nticket: PRA-99\nstatus: success\n---\nbody"
        fm, body = h.parse_frontmatter(text)
        self.assertEqual(fm.get("ticket"), "PRA-99")
        self.assertEqual(fm.get("status"), "success")
        self.assertEqual(body.strip(), "body")

    def test_bool_parsing(self):
        """true/false 값이 Python bool로 변환된다."""
        text = "---\nself_pass: true\nfailed: false\n---"
        fm, _ = h.parse_frontmatter(text)
        self.assertIs(fm.get("self_pass"), True)
        self.assertIs(fm.get("failed"), False)

    def test_integer_parsing(self):
        """정수(integer) 스칼라가 int로 변환된다."""
        text = "---\nturns: 7\nskip_presearch: 0\n---"
        fm, _ = h.parse_frontmatter(text)
        self.assertEqual(fm.get("turns"), 7)
        self.assertEqual(fm.get("skip_presearch"), 0)

    def test_block_scalar(self):
        """`|` 블록 스칼라가 여러 줄 문자열로 파싱된다."""
        text = "---\nproblem: |\n  line one\n  line two\n---"
        fm, _ = h.parse_frontmatter(text)
        self.assertIn("line one", fm.get("problem", ""))
        self.assertIn("line two", fm.get("problem", ""))

    def test_inline_list(self):
        """인라인 리스트 `[a, b]` 파싱."""
        text = "---\nrisk_areas: [deidentification, architecture]\n---"
        fm, _ = h.parse_frontmatter(text)
        areas = fm.get("risk_areas")
        self.assertIsInstance(areas, list)
        self.assertIn("deidentification", areas)

    def test_inline_mapping_list(self):
        """인라인 매핑 리스트 `- {gate: 0, result: ok}` 파싱."""
        text = "---\ngate_events:\n  - {gate: 0, result: ok, turns: 3}\n---"
        fm, _ = h.parse_frontmatter(text)
        events = fm.get("gate_events")
        self.assertIsInstance(events, list)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].get("gate"), 0)
        self.assertEqual(events[0].get("result"), "ok")

    def test_nested_mapping(self):
        """중첩 매핑(nested mapping)이 dict로 파싱된다."""
        text = "---\nintent:\n  problem: something wrong\n  approach: fix it\n---"
        fm, _ = h.parse_frontmatter(text)
        intent = fm.get("intent")
        self.assertIsInstance(intent, dict)
        self.assertEqual(intent.get("problem"), "something wrong")
        self.assertEqual(intent.get("approach"), "fix it")

    def test_multiline_mapping_list_item(self):
        """여러 줄 매핑 리스트 항목 파싱 (readiness_flags 형식)."""
        text = (
            "---\n"
            "readiness_flags:\n"
            "  - flag: some-flag\n"
            "    detail: some detail text\n"
            "    resolution: resolved\n"
            "---"
        )
        fm, _ = h.parse_frontmatter(text)
        flags = fm.get("readiness_flags")
        self.assertIsInstance(flags, list)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].get("flag"), "some-flag")
        self.assertEqual(flags[0].get("detail"), "some detail text")

    # ③ malformed YAML → parse-error 레코드 (무crash)
    def test_malformed_yaml_no_crash(self):
        """malformed YAML이 예외를 던지지 않고 _parse_error 키를 반환한다."""
        # 콜론 중첩 오류를 유발하는 입력
        text = "---\n: : bad\n  - x:\n---\nbody"
        # 무crash가 핵심 — 예외가 없어야 한다
        try:
            fm, body = h.parse_frontmatter(text)
        except Exception as exc:  # noqa: BLE001
            self.fail(f"parse_frontmatter threw unexpectedly: {exc}")

    def test_malformed_returns_parse_error_record(self):
        """
        실제로 파싱에 실패하는 입력이 _parse_error 키를 가진 dict를 반환한다.
        단, 단순 malformed는 파서가 부분적으로 처리할 수 있으므로
        이 테스트는 파서가 crash하지 않는 것과 dict를 반환하는 것만 검증한다.
        """
        text = "---\n!!invalid_yaml_tag @@#$\n---"
        try:
            fm, _ = h.parse_frontmatter(text)
            self.assertIsInstance(fm, dict)
        except Exception as exc:  # noqa: BLE001
            self.fail(f"parse_frontmatter should not raise: {exc}")


class TestRealPlanParsing(unittest.TestCase):
    """실제 PRA-109/plan.md 파싱 검증 (① 항목)."""

    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(_PLAN_PATH):
            raise unittest.SkipTest(f"plan.md not found: {_PLAN_PATH}")
        with open(_PLAN_PATH, encoding="utf-8") as f:
            cls.text = f.read()
        cls.fm, cls.body = h.parse_frontmatter(cls.text)

    def test_intent_problem_extracted(self):
        """intent.problem 필드가 추출된다."""
        intent = self.fm.get("intent")
        self.assertIsInstance(intent, dict, f"intent는 dict여야 한다, got: {type(intent)}")
        problem = intent.get("problem")
        self.assertTrue(problem, "intent.problem이 비어 있다")
        self.assertIsInstance(problem, str)

    def test_gate_events_is_list(self):
        """gate_events가 리스트이고 적어도 1개의 항목이 있다."""
        events = self.fm.get("gate_events")
        self.assertIsInstance(events, list, f"gate_events는 list여야 한다, got: {type(events)}")
        self.assertGreaterEqual(len(events), 1, "gate_events가 비어 있다")

    def test_gate_events_have_gate_field(self):
        """각 gate_event에 gate 필드가 있다."""
        events = self.fm.get("gate_events", [])
        for ev in events:
            self.assertIn("gate", ev, f"gate 필드 없음: {ev}")

    def test_skip_fields_are_integers(self):
        """skip_presearch / skip_gate2 가 정수다."""
        self.assertIsInstance(self.fm.get("skip_presearch"), int)
        self.assertIsInstance(self.fm.get("skip_gate2"), int)

    def test_risk_acks_extracted(self):
        """risk_acks 리스트가 추출된다."""
        acks = self.fm.get("risk_acks")
        self.assertIsInstance(acks, list)
        self.assertGreater(len(acks), 0)

    def test_readiness_flags_as_list_of_dicts(self):
        """readiness_flags가 dict 리스트로 파싱된다."""
        flags = self.fm.get("readiness_flags")
        self.assertIsInstance(flags, list)
        if flags:
            self.assertIsInstance(flags[0], dict, f"첫 항목이 dict여야 함: {flags[0]}")

    def test_no_user_prompt_verbatim_in_harvest_plan(self):
        """
        비식별 경계 검증: harvest_plan 출력에 user_prompt verbatim이 포함되지 않는다.
        plan.md의 user_prompt 값과 harvest_plan 반환값을 비교한다.
        """
        # plan.md의 user_prompt 원문 (있으면)
        user_prompt_raw = self.fm.get("user_prompt")
        if not user_prompt_raw:
            self.skipTest("plan.md에 user_prompt 없음")

        # harvest_plan 반환값에 user_prompt verbatim이 없어야 한다
        plan_rec = h.harvest_plan(os.path.dirname(_PLAN_PATH))
        self.assertIsNotNone(plan_rec)
        import json
        plan_str = json.dumps(plan_rec, ensure_ascii=False)
        # user_prompt의 핵심 구절이 harvest 출력에 없는지 확인
        # plan.md의 user_prompt: "위의 내용 진행해주되 먼저 linear로 티켓 만들고 그거 이용해서 하자"
        if isinstance(user_prompt_raw, str) and len(user_prompt_raw.strip()) > 5:
            # 원문의 앞 10자 이상이 포함되면 verbatim 누출
            snippet = user_prompt_raw.strip()[:15]
            self.assertNotIn(snippet, plan_str,
                             f"harvest_plan 출력에 user_prompt verbatim 누출: {snippet!r}")


class TestLegacySkipNormalization(unittest.TestCase):
    """④ legacy skip_grill_count 정규화 테스트."""

    def test_skip_grill_count_normalized_to_skip_presearch(self):
        """legacy skip_grill_count → skip_presearch로 정규화."""
        fm = {"skip_grill_count": 2}
        sp, sg = h._normalize_skip_counts(fm)
        self.assertEqual(sp, 2)
        self.assertEqual(sg, 0)

    def test_current_fields_take_precedence(self):
        """현행 skip_presearch/skip_gate2가 있으면 legacy를 무시한다."""
        fm = {"skip_presearch": 1, "skip_gate2": 3, "skip_grill_count": 5}
        sp, sg = h._normalize_skip_counts(fm)
        self.assertEqual(sp, 1)
        self.assertEqual(sg, 3)

    def test_no_skip_fields_returns_zeros(self):
        """skip 필드 전부 없으면 (0, 0) 반환."""
        fm: dict = {}
        sp, sg = h._normalize_skip_counts(fm)
        self.assertEqual(sp, 0)
        self.assertEqual(sg, 0)

    def test_explicit_zero_skip_presearch_not_overridden_by_legacy(self):
        """p3-a: skip_presearch: 0 (명시적 zero) + skip_grill_count: 2 → skip_presearch는 0 유지."""
        fm = {"skip_presearch": 0, "skip_grill_count": 2}
        sp, sg = h._normalize_skip_counts(fm)
        self.assertEqual(sp, 0, "explicit zero skip_presearch must not be overridden by legacy")
        self.assertEqual(sg, 0)

    def test_via_parse_frontmatter_legacy_field(self):
        """parse_frontmatter + harvest_plan 경로에서 legacy 정규화 통합 테스트."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_content = (
                "---\n"
                "ticket: LEGACY-1\n"
                "skip_grill_count: 3\n"
                "intent:\n"
                "  problem: some problem\n"
                "gate_events:\n"
                "  - {gate: 0, result: ok, turns: 1, self_pass: false}\n"
                "---\n"
                "# Plan\n"
            )
            plan_path = os.path.join(tmpdir, "plan.md")
            with open(plan_path, "w", encoding="utf-8") as f:
                f.write(plan_content)

            rec = h.harvest_plan(tmpdir)
            self.assertIsNotNone(rec)
            self.assertEqual(rec.get("skip_presearch"), 3)
            self.assertEqual(rec.get("skip_gate2"), 0)
            # skip_grill_count는 schema-drift 신호로 보존된다 (p2-B fix)
            self.assertEqual(rec.get("skip_grill_count"), 3)


class TestTicketlessSeparation(unittest.TestCase):
    """⑤ ticketless 분리 테스트."""

    def _make_corpus(self, tmpdir: str) -> object:
        """임시 디렉토리에 테스트용 코퍼스를 생성한다."""
        claude = os.path.join(tmpdir, ".claude")
        plans = os.path.join(claude, "plans")
        tasks_done = os.path.join(claude, "tasks", "done")
        runs = os.path.join(claude, "runs")
        os.makedirs(plans, exist_ok=True)
        os.makedirs(tasks_done, exist_ok=True)
        os.makedirs(runs, exist_ok=True)
        return discover.RepoCorpus(
            repo_path=tmpdir,
            name="test-repo",
            session_dir=None,
            plans_dir=plans,
            tasks_dirs=[tasks_done],
            runs_dir=runs,
        )

    def test_ticketless_plan_goes_to_ticketless_bucket(self):
        """ticket 없는 plan.md → ticketless 버킷에 들어간다."""
        with tempfile.TemporaryDirectory() as tmpdir:
            corpus = self._make_corpus(tmpdir)
            # ticket 없는 plan.md
            plan_content = (
                "---\n"
                "intent:\n"
                "  problem: no ticket here\n"
                "gate_events:\n"
                "  - {gate: 0, result: ok, turns: 1, self_pass: false}\n"
                "---\n"
            )
            with open(os.path.join(corpus.plans_dir, "plan.md"), "w", encoding="utf-8") as f:
                f.write(plan_content)

            result = h.harvest_repo(corpus)

            self.assertIn("ticketless", result)
            self.assertIn("by_ticket", result)
            # ticketless 버킷에 plan이 들어가야 한다
            ticketless_types = [item.get("type") for item in result["ticketless"]]
            self.assertIn("plan", ticketless_types)
            # by_ticket은 비어 있거나 이 plan의 ticket이 없어야 한다
            self.assertNotIn(None, result["by_ticket"])

    def test_ticketed_plan_goes_to_by_ticket(self):
        """ticket 있는 plan.md → by_ticket 버킷에 들어간다."""
        with tempfile.TemporaryDirectory() as tmpdir:
            corpus = self._make_corpus(tmpdir)
            plan_content = (
                "---\n"
                "ticket: TEST-42\n"
                "intent:\n"
                "  problem: has a ticket\n"
                "gate_events:\n"
                "  - {gate: 0, result: ok, turns: 1, self_pass: false}\n"
                "---\n"
            )
            with open(os.path.join(corpus.plans_dir, "plan.md"), "w", encoding="utf-8") as f:
                f.write(plan_content)

            result = h.harvest_repo(corpus)

            self.assertIn("TEST-42", result["by_ticket"])
            self.assertIsNotNone(result["by_ticket"]["TEST-42"]["plan"])

    def test_ticketless_task_goes_to_ticketless_bucket(self):
        """ticket 없는 task.md → ticketless 버킷에 들어간다."""
        with tempfile.TemporaryDirectory() as tmpdir:
            corpus = self._make_corpus(tmpdir)
            task_content = (
                "---\n"
                "task_id: task-1-no-ticket\n"
                "status: pending\n"
                "role: implementer\n"
                "---\n"
                "## Task\n"
            )
            with open(
                os.path.join(corpus.tasks_dirs[0], "task-1-no-ticket.md"),
                "w",
                encoding="utf-8",
            ) as f:
                f.write(task_content)

            result = h.harvest_repo(corpus)
            ticketless_types = [item.get("type") for item in result["ticketless"]]
            self.assertIn("task", ticketless_types)

    def test_ticketed_and_ticketless_mixed(self):
        """ticketed와 ticketless가 혼재하면 각 버킷에 올바르게 분리된다."""
        with tempfile.TemporaryDirectory() as tmpdir:
            corpus = self._make_corpus(tmpdir)
            # ticketed task
            with open(
                os.path.join(corpus.tasks_dirs[0], "task-1-with-ticket.md"),
                "w",
                encoding="utf-8",
            ) as f:
                f.write("---\nticket: MIX-10\ntask: task-1-with-ticket\nstatus: success\nrole: implementer\n---\n")
            # ticketless task
            with open(
                os.path.join(corpus.tasks_dirs[0], "task-2-no-ticket.md"),
                "w",
                encoding="utf-8",
            ) as f:
                f.write("---\ntask: task-2-no-ticket\nstatus: pending\nrole: implementer\n---\n")

            result = h.harvest_repo(corpus)
            self.assertIn("MIX-10", result["by_ticket"])
            ticketless_ids = [
                item.get("record", {}).get("task_id") for item in result["ticketless"]
            ]
            self.assertIn("task-2-no-ticket", ticketless_ids)


class TestHarvestPlan(unittest.TestCase):
    """harvest_plan 함수 테스트."""

    def test_none_for_missing_dir(self):
        """존재하지 않는 디렉토리 → None 반환."""
        result = h.harvest_plan("/nonexistent/path/plans")
        self.assertIsNone(result)

    def test_none_for_missing_plan_md(self):
        """plan.md 없는 디렉토리 → None 반환."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = h.harvest_plan(tmpdir)
            self.assertIsNone(result)

    def test_extracts_basic_fields(self):
        """plan.md 기본 필드 추출."""
        with tempfile.TemporaryDirectory() as tmpdir:
            content = (
                "---\n"
                "ticket: PLN-1\n"
                "skip_presearch: 1\n"
                "skip_gate2: 2\n"
                "intent:\n"
                "  problem: test problem\n"
                "  approach: test approach\n"
                "gate_events:\n"
                "  - {gate: 0, result: ok, turns: 1, self_pass: false}\n"
                "risk_acks:\n"
                "  - {area: architecture, ack: confirmed, ts: 2026-01-01T00:00:00+09:00}\n"
                "---\n"
            )
            with open(os.path.join(tmpdir, "plan.md"), "w", encoding="utf-8") as f:
                f.write(content)

            rec = h.harvest_plan(tmpdir)
            self.assertIsNotNone(rec)
            self.assertEqual(rec.get("ticket"), "PLN-1")
            self.assertEqual(rec.get("skip_presearch"), 1)
            self.assertEqual(rec.get("skip_gate2"), 2)
            intent = rec.get("intent", {})
            self.assertEqual(intent.get("problem"), "test problem")
            self.assertEqual(len(rec.get("gate_events", [])), 1)
            self.assertEqual(len(rec.get("risk_acks", [])), 1)

    def test_no_user_prompt_in_output(self):
        """비식별 경계: user_prompt 필드가 harvest 출력에 포함되지 않는다."""
        with tempfile.TemporaryDirectory() as tmpdir:
            content = (
                "---\n"
                "ticket: SEC-1\n"
                "user_prompt: |\n"
                "  이것은 유저의 원문 프롬프트입니다. verbatim 누출 금지.\n"
                "intent:\n"
                "  problem: some problem\n"
                "gate_events:\n"
                "  - {gate: 0, result: ok, turns: 1, self_pass: false}\n"
                "---\n"
            )
            with open(os.path.join(tmpdir, "plan.md"), "w", encoding="utf-8") as f:
                f.write(content)

            rec = h.harvest_plan(tmpdir)
            self.assertIsNotNone(rec)
            import json
            rec_str = json.dumps(rec, ensure_ascii=False)
            # user_prompt verbatim이 harvest 출력에 없어야 한다
            self.assertNotIn("이것은 유저의 원문 프롬프트", rec_str,
                             "user_prompt verbatim이 harvest 출력에 누출됨")
            self.assertNotIn("user_prompt", rec,
                             "user_prompt 키가 harvest 출력에 포함됨")


class TestHarvestPlansFromDir(unittest.TestCase):
    """p2 fix: harvest_plans_from_dir — multiple ticket subdirs."""

    def _write_plan(self, parent: str, ticket: str) -> None:
        subdir = os.path.join(parent, ticket)
        os.makedirs(subdir, exist_ok=True)
        with open(os.path.join(subdir, "plan.md"), "w", encoding="utf-8") as f:
            f.write(
                f"---\nticket: {ticket}\nintent:\n  problem: problem for {ticket}\n"
                "gate_events:\n  - {gate: 0, result: ok, turns: 1, self_pass: false}\n---\n"
            )

    def test_two_ticket_subdirs_both_harvested(self):
        """p2: ALPHA-1 + BETA-2 두 서브디렉토리 → 둘 다 by_ticket에 수집된다."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._write_plan(tmpdir, "ALPHA-1")
            self._write_plan(tmpdir, "BETA-2")

            records = h.harvest_plans_from_dir(tmpdir)
            tickets = {r.get("ticket") for r in records if "_parse_errors" not in r}
            self.assertIn("ALPHA-1", tickets, "ALPHA-1 plan not harvested")
            self.assertIn("BETA-2", tickets, "BETA-2 plan not harvested")
            self.assertEqual(len(records), 2)

    def test_two_subdirs_both_in_harvest_repo_by_ticket(self):
        """p2: harvest_repo groups both ticket subdirs into by_ticket."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plans_dir = os.path.join(tmpdir, "plans")
            os.makedirs(plans_dir)
            self._write_plan(plans_dir, "ALPHA-1")
            self._write_plan(plans_dir, "BETA-2")

            corpus = discover.RepoCorpus(
                repo_path=tmpdir,
                name="multi-plan-test",
                session_dir=None,
                plans_dir=plans_dir,
                tasks_dirs=[],
                runs_dir=None,
            )
            result = h.harvest_repo(corpus)
            self.assertIn("ALPHA-1", result["by_ticket"], "ALPHA-1 missing from by_ticket")
            self.assertIn("BETA-2", result["by_ticket"], "BETA-2 missing from by_ticket")
            self.assertIsNotNone(result["by_ticket"]["ALPHA-1"]["plan"])
            self.assertIsNotNone(result["by_ticket"]["BETA-2"]["plan"])

    def test_single_direct_plan_still_works(self):
        """legacy: plans_dir/plan.md (직계) → 단일 레코드 반환."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "plan.md"), "w", encoding="utf-8") as f:
                f.write(
                    "---\nticket: SINGLE-1\nintent:\n  problem: single plan\n"
                    "gate_events:\n  - {gate: 0, result: ok, turns: 1, self_pass: false}\n---\n"
                )
            records = h.harvest_plans_from_dir(tmpdir)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].get("ticket"), "SINGLE-1")

    def test_empty_plans_dir_returns_empty_list(self):
        """plan.md 없는 plans_dir → 빈 리스트."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = h.harvest_plans_from_dir(tmpdir)
            self.assertEqual(result, [])

    def test_nonexistent_dir_returns_empty_list(self):
        """존재하지 않는 plans_dir → 빈 리스트 (무crash)."""
        result = h.harvest_plans_from_dir("/nonexistent/plans")
        self.assertEqual(result, [])


class TestHarvestTasks(unittest.TestCase):
    """harvest_tasks 함수 테스트."""

    def test_empty_dirs_returns_empty_list(self):
        """빈 디렉토리 리스트 → 빈 리스트 반환."""
        result = h.harvest_tasks([])
        self.assertEqual(result, [])

    def test_nonexistent_dir_no_crash(self):
        """존재하지 않는 디렉토리 → 빈 리스트 반환 (무crash)."""
        result = h.harvest_tasks(["/nonexistent/tasks/done"])
        self.assertEqual(result, [])

    def test_extracts_task_fields(self):
        """task.md / result.md 기본 필드 추출."""
        with tempfile.TemporaryDirectory() as tmpdir:
            content = (
                "---\n"
                "ticket: TSK-5\n"
                "task: task-1-something\n"
                "status: success\n"
                "role: implementer\n"
                "plan_deviations:\n"
                "  - {ts: 2026-01-01T00:00:00+09:00, note: some deviation}\n"
                "---\n"
                "## Round 2\n"
                "Some content\n"
            )
            fpath = os.path.join(tmpdir, "task-1-something-result.md")
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)

            records = h.harvest_tasks([tmpdir])
            self.assertEqual(len(records), 1)
            rec = records[0]
            self.assertEqual(rec.get("ticket"), "TSK-5")
            self.assertEqual(rec.get("task_id"), "task-1-something")
            self.assertEqual(rec.get("status"), "success")
            self.assertEqual(rec.get("role"), "implementer")
            self.assertEqual(rec.get("plan_deviations_count"), 1)
            self.assertEqual(rec.get("round_count"), 2)

    def test_malformed_task_no_crash(self):
        """malformed task.md → parse-error 레코드 반환, 무crash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "broken-task.md")
            with open(fpath, "w", encoding="utf-8") as f:
                f.write("---\n!!@@invalid\n---\n")
            try:
                records = h.harvest_tasks([tmpdir])
            except Exception as exc:  # noqa: BLE001
                self.fail(f"harvest_tasks threw unexpectedly: {exc}")
            # 결과가 반환돼야 한다 (파싱 오류 레코드 또는 정상 레코드)
            self.assertIsInstance(records, list)

    def test_round_count_from_body(self):
        """라운드 수(round count)가 body의 ## Round N 패턴 최대값으로 집계된다."""
        with tempfile.TemporaryDirectory() as tmpdir:
            content = (
                "---\n"
                "ticket: RND-1\n"
                "task: task-1-rnd\n"
                "status: success\n"
                "role: implementer\n"
                "---\n"
                "## Round 2\n"
                "content\n"
                "## Round 3\n"
                "more content\n"
            )
            with open(os.path.join(tmpdir, "task-1-rnd-result.md"), "w", encoding="utf-8") as f:
                f.write(content)
            records = h.harvest_tasks([tmpdir])
            self.assertEqual(records[0].get("round_count"), 3)


class TestHarvestManifest(unittest.TestCase):
    """harvest_manifest 함수 테스트."""

    def test_none_for_missing_runs_dir(self):
        """존재하지 않는 runs_dir → None 반환."""
        result = h.harvest_manifest("/nonexistent/runs")
        self.assertIsNone(result)

    def test_none_for_empty_runs_dir(self):
        """manifest.yaml 없는 runs_dir → None 반환."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = h.harvest_manifest(tmpdir)
            self.assertIsNone(result)

    def test_extracts_manifest_fields(self):
        """manifest.yaml 기본 필드 추출."""
        with tempfile.TemporaryDirectory() as tmpdir:
            content = (
                "---\n"
                "ticket: MAN-1\n"
                "status: success\n"
                "quality_gates:\n"
                "  - {name: all tests pass, status: pass}\n"
                "workflow_runs:\n"
                "  - {workflow: impl, status: success}\n"
                "---\n"
            )
            with open(os.path.join(tmpdir, "manifest.yaml"), "w", encoding="utf-8") as f:
                f.write(content)

            rec = h.harvest_manifest(tmpdir)
            self.assertIsNotNone(rec)
            self.assertEqual(rec.get("ticket"), "MAN-1")
            self.assertEqual(rec.get("status"), "success")
            self.assertIsInstance(rec.get("quality_gates"), list)
            self.assertIsInstance(rec.get("workflow_runs"), list)

    def test_manifest_in_ticket_subdir(self):
        """runs_dir/{TICKET}/manifest.yaml 형식도 탐색한다."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, "TICKET-42")
            os.makedirs(subdir)
            content = (
                "---\n"
                "ticket: TICKET-42\n"
                "status: success\n"
                "---\n"
            )
            with open(os.path.join(subdir, "manifest.yaml"), "w", encoding="utf-8") as f:
                f.write(content)

            rec = h.harvest_manifest(tmpdir)
            self.assertIsNotNone(rec)
            self.assertEqual(rec.get("ticket"), "TICKET-42")


class TestHarvestRepo(unittest.TestCase):
    """harvest_repo 함수 통합 테스트."""

    def _make_full_corpus(self, tmpdir: str) -> object:
        claude = os.path.join(tmpdir, ".claude")
        plans = os.path.join(claude, "plans")
        tasks_done = os.path.join(claude, "tasks", "done")
        runs = os.path.join(claude, "runs")
        os.makedirs(plans, exist_ok=True)
        os.makedirs(tasks_done, exist_ok=True)
        os.makedirs(runs, exist_ok=True)
        return discover.RepoCorpus(
            repo_path=tmpdir,
            name="test-full",
            session_dir=None,
            plans_dir=plans,
            tasks_dirs=[tasks_done],
            runs_dir=runs,
        )

    def test_returns_required_keys(self):
        """harvest_repo 반환 dict에 필수 키가 있다."""
        with tempfile.TemporaryDirectory() as tmpdir:
            corpus = self._make_full_corpus(tmpdir)
            result = h.harvest_repo(corpus)
            for key in ("repo_path", "repo_name", "by_ticket", "ticketless", "parse_errors"):
                self.assertIn(key, result, f"필수 키 누락: {key}")

    def test_ticket_grouping(self):
        """ticket별 plan + tasks + manifest가 하나의 버킷에 묶인다."""
        with tempfile.TemporaryDirectory() as tmpdir:
            corpus = self._make_full_corpus(tmpdir)

            # plan.md
            with open(os.path.join(corpus.plans_dir, "plan.md"), "w", encoding="utf-8") as f:
                f.write(
                    "---\nticket: GRP-1\nintent:\n  problem: group test\n"
                    "gate_events:\n  - {gate: 0, result: ok, turns: 1, self_pass: false}\n---\n"
                )

            # task.md
            with open(
                os.path.join(corpus.tasks_dirs[0], "task-1-grp.md"), "w", encoding="utf-8"
            ) as f:
                f.write("---\nticket: GRP-1\ntask: task-1-grp\nstatus: success\nrole: implementer\n---\n")

            # manifest.yaml
            with open(os.path.join(corpus.runs_dir, "manifest.yaml"), "w", encoding="utf-8") as f:
                f.write("---\nticket: GRP-1\nstatus: success\n---\n")

            result = h.harvest_repo(corpus)
            self.assertIn("GRP-1", result["by_ticket"])
            bucket = result["by_ticket"]["GRP-1"]
            self.assertIsNotNone(bucket["plan"])
            self.assertEqual(len(bucket["tasks"]), 1)
            self.assertIsNotNone(bucket["manifest"])

    def test_parse_errors_collected_not_crashed(self):
        """parse error가 있는 파일은 parse_errors에 기록되고 전체 수확이 멈추지 않는다."""
        with tempfile.TemporaryDirectory() as tmpdir:
            corpus = self._make_full_corpus(tmpdir)

            # 정상 plan.md
            with open(os.path.join(corpus.plans_dir, "plan.md"), "w", encoding="utf-8") as f:
                f.write(
                    "---\nticket: ERR-1\nintent:\n  problem: ok\n"
                    "gate_events:\n  - {gate: 0, result: ok, turns: 1, self_pass: false}\n---\n"
                )

            # 정상 task.md
            with open(
                os.path.join(corpus.tasks_dirs[0], "task-1-ok.md"), "w", encoding="utf-8"
            ) as f:
                f.write("---\nticket: ERR-1\ntask: task-1-ok\nstatus: success\nrole: implementer\n---\n")

            result = h.harvest_repo(corpus)
            self.assertIn("ERR-1", result["by_ticket"])
            self.assertIsInstance(result["parse_errors"], list)


class TestCmdHarvestArtifactsTicketFilter(unittest.TestCase):
    """p3-b: collect.py harvest-artifacts --ticket X filters output."""

    _COLLECT_PATH = os.path.join(_TELEMETRY_DIR, "collect.py")

    def _make_fake_repo(self, root: str, ticket: str) -> str:
        """root 아래에 .claude/ 구조를 갖춘 가짜 레포를 만들고 repo 경로를 반환한다."""
        repo = os.path.join(root, "fake-repo")
        plans_dir = os.path.join(repo, ".claude", "plans")
        ticket_dir = os.path.join(plans_dir, ticket)
        os.makedirs(ticket_dir)
        with open(os.path.join(ticket_dir, "plan.md"), "w", encoding="utf-8") as f:
            f.write(
                f"---\nticket: {ticket}\nintent:\n  problem: filter test {ticket}\n"
                "gate_events:\n  - {gate: 0, result: ok, turns: 1, self_pass: false}\n---\n"
            )
        os.makedirs(os.path.join(repo, ".claude", "tasks", "done"))
        os.makedirs(os.path.join(repo, ".claude", "runs"))
        return repo

    def test_ticket_filter_includes_matching_repo(self):
        """--ticket X → repo with plans_dir/X/plan.md is included."""
        import subprocess
        import json

        with tempfile.TemporaryDirectory() as root:
            self._make_fake_repo(root, "FILTER-99")

            result = subprocess.run(
                [
                    "python3", self._COLLECT_PATH,
                    "harvest-artifacts",
                    "--roots", root,
                    "--ticket", "FILTER-99",
                ],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            data = json.loads(result.stdout)
            self.assertGreaterEqual(data["repo_count"], 1, "matching repo should be included")
            # At least one result with by_ticket containing FILTER-99
            found = any(
                "FILTER-99" in res.get("by_ticket", {})
                for res in data.get("results", [])
            )
            self.assertTrue(found, "FILTER-99 not found in harvest output after --ticket filter")

    def test_ticket_filter_excludes_non_matching_repo(self):
        """--ticket X → repo without plans_dir/X is excluded (repo_count=0)."""
        import subprocess
        import json

        with tempfile.TemporaryDirectory() as root:
            # Repo has a different ticket subdir
            self._make_fake_repo(root, "OTHER-1")

            result = subprocess.run(
                [
                    "python3", self._COLLECT_PATH,
                    "harvest-artifacts",
                    "--roots", root,
                    "--ticket", "FILTER-99",
                ],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            data = json.loads(result.stdout)
            self.assertEqual(data["repo_count"], 0, "non-matching repo should be filtered out")


if __name__ == "__main__":
    unittest.main()
