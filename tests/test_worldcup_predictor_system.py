import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = ROOT / "scripts" / name
    if not path.exists():
        raise AssertionError(f"missing script: {path}")
    spec = importlib.util.spec_from_file_location(name.removesuffix(".py"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WorldCupPredictorSystemTest(unittest.TestCase):
    def test_source_snapshot_apply_writes_raw_file_and_manifest(self):
        init_module = load_script("worldcup_edition_init.py")
        snapshot_module = load_script("worldcup_source_snapshot_tool.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_module.initialize_edition(root=root, edition="2098", now="2026-06-09T12:00:00+08:00")

            result = snapshot_module.snapshot_source(
                root=root,
                edition="2098",
                source_id="fifa-squad-lists-pdf",
                mode="apply",
                now="2026-06-09T12:30:00+08:00",
                fetcher=lambda url: b"%PDF fake squad list",
            )

            self.assertEqual(result["status"], "snapshot_written")
            self.assertEqual(result["summary"]["fetches_performed"], 1)
            self.assertEqual(result["summary"]["raw_writes_performed"], 2)
            snapshot_path = Path(result["snapshot_path"])
            manifest_path = Path(result["manifest_path"])
            self.assertTrue(snapshot_path.exists())
            self.assertTrue(manifest_path.exists())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["source_id"], "fifa-squad-lists-pdf")
            self.assertEqual(manifest["sha256"], result["sha256"])

    def test_source_snapshot_apply_records_fetch_failure_manifest(self):
        init_module = load_script("worldcup_edition_init.py")
        snapshot_module = load_script("worldcup_source_snapshot_tool.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_module.initialize_edition(root=root, edition="2098", now="2026-06-09T12:00:00+08:00")

            def failing_fetcher(url: str) -> bytes:
                raise RuntimeError("rate limit exceeded")

            result = snapshot_module.snapshot_source(
                root=root,
                edition="2098",
                source_id="fifa-men-ranking",
                mode="apply",
                now="2026-06-09T12:30:00+08:00",
                fetcher=failing_fetcher,
            )

            self.assertEqual(result["status"], "blocked_fetch_failed")
            self.assertIn("source_fetch_failed", result["blockers"])
            self.assertEqual(result["summary"]["fetches_performed"], 1)
            manifest_path = Path(result["manifest_path"])
            self.assertTrue(manifest_path.exists())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["error_type"], "RuntimeError")
            self.assertEqual(manifest["summary"]["raw_writes_performed"], 1)

    def test_fifa_squad_table_parser_extracts_team_players_and_coach(self):
        parser_module = load_script("fifa_squad_pdf_parser.py")
        page_text = "\n".join(
            [
                "SQUAD LIST",
                "FIFA World Cup 2026™",
                "Argentina (ARG)",
                "Tuesday, 9 June 2026 | 00:53 UTC | Version 1 | Page 2 / 48",
            ]
        )
        rows = [
            ["#", "POS", "PLAYER NAME", None, "FIRST NAME(S)", "LAST NAME(S)", "NAME ON SHIRT", None, "DOB", "CLUB", None, "HEIGHT (CM)"],
            ["10", "FW", "MESSI Lionel", None, "Lionel Andrés", "MESSI", "MESSI", None, "24/06/1987", "Inter Miami CF (USA)", None, "170"],
            ["25", "DF", "ULMASALIYEV Avazbek", None, "Avazbek", "ULMASALIYEV", None, "ULMASALIYEV", "27/03/2000", None, "OKMK FK (UZB)", None, "187"],
            ["ROLE", None, None, "COACH NAME", None, "FIRST NAME(S)", None, "LAST NAME(S)", None, None, "NATIONALITY", None],
            ["Head coach", None, None, "SCALONI Lionel", None, "Lionel Sebastián", None, "SCALONI", None, None, "Argentina", None],
        ]

        parsed = parser_module.parse_team_page(page_text=page_text, table_rows=rows, edition="2098", page_number=2)

        self.assertEqual(parsed["team"]["name"], "Argentina")
        self.assertEqual(parsed["team"]["code"], "ARG")
        self.assertEqual(parsed["coach"]["coach_name"], "SCALONI Lionel")
        self.assertEqual(len(parsed["players"]), 2)
        messi = parsed["players"][0]
        self.assertEqual(messi["shirt_number"], 10)
        self.assertEqual(messi["position"], "FW")
        self.assertEqual(messi["player_name"], "MESSI Lionel")
        self.assertEqual(messi["first_names"], "Lionel Andrés")
        self.assertEqual(messi["last_names"], "MESSI")
        self.assertEqual(messi["name_on_shirt"], "MESSI")
        self.assertEqual(messi["dob"], "1987-06-24")
        self.assertEqual(messi["club"], "Inter Miami CF (USA)")
        shifted = parsed["players"][1]
        self.assertEqual(shifted["club"], "OKMK FK (UZB)")

    def test_edition_init_creates_isolated_knowledge_base_and_104_match_ledger(self):
        module = load_script("worldcup_edition_init.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = module.initialize_edition(root=root, edition="2098", now="2026-06-09T12:00:00+08:00")

            self.assertEqual(result["edition"], "2098")
            self.assertEqual(result["summary"]["match_count"], 104)
            self.assertEqual(result["summary"]["group_stage_matches"], 72)
            self.assertEqual(result["summary"]["knockout_matches"], 32)

            ledger_path = root / "_meta/projects/世界杯预测/data/editions/2098/match-ledger.json"
            registry_path = root / "raw/体育/世界杯/2098/source-registry.json"
            moc_path = root / "wiki/体育/世界杯/2098/synthesis/MOC-世界杯2098.md"
            self.assertTrue(ledger_path.exists())
            self.assertTrue(registry_path.exists())
            self.assertTrue(moc_path.exists())

            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            match_ids = [match["match_id"] for match in ledger["matches"]]
            self.assertEqual(len(match_ids), 104)
            self.assertEqual(len(set(match_ids)), 104)
            self.assertIn("worldcup_match_ledger_records_all_104_matches", ledger["safety_invariants"])

    def test_standalone_repo_root_uses_local_data_directory(self):
        module = load_script("worldcup_edition_init.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "scripts" / "worldcup_core.py").write_text("def build_play_card():\n    return {}\n", encoding="utf-8")
            (root / "schema").mkdir()

            module.initialize_edition(root=root, edition="2098", now="2026-06-09T12:00:00+08:00")

            self.assertTrue((root / "data/editions/2098/match-ledger.json").exists())
            self.assertFalse((root / "_meta/projects/世界杯预测/data/editions/2098/match-ledger.json").exists())

    def test_standalone_export_copies_runtime_and_edition_knowledge_base(self):
        init_module = load_script("worldcup_edition_init.py")
        export_module = load_script("worldcup_export_standalone.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            output = Path(tmp) / "export"
            init_module.initialize_edition(root=root, edition="2098", now="2026-06-09T12:00:00+08:00")
            leaky_path = root / "_meta/projects/世界杯预测/data/editions/2098/reports/posters/leaky-path.json"
            leaky_path.parent.mkdir(parents=True, exist_ok=True)
            leaky_path.write_text(json.dumps({"path": str(root / "_meta/projects/世界杯预测/data/editions/2098/match-ledger.json")}), encoding="utf-8")

            result = export_module.export_standalone(root=root, edition="2098", output=output, now="2026-06-09T12:30:00+08:00")

            self.assertEqual(result["status"], "export_written")
            self.assertGreaterEqual(result["path_sanitization"]["changed_files"], 1)
            self.assertTrue((output / "scripts/worldcup_core.py").exists())
            self.assertTrue((output / "schema/match-ledger.schema.json").exists())
            self.assertTrue((output / "SKILL.md").exists())
            self.assertTrue((output / "skills/fifa-winner-skill/SKILL.md").exists())
            self.assertTrue((output / "TODO.md").exists())
            self.assertTrue((output / "LICENSE").exists())
            self.assertTrue((output / "install_as_skill.sh").exists())
            self.assertTrue((output / ".github/workflows/ci.yml").exists())
            self.assertTrue((output / "examples/sample-prediction-report.json").exists())
            self.assertTrue((output / "examples/sample-poster-manifest.json").exists())
            self.assertTrue((output / "examples/sample-poster-result-blocked.json").exists())
            self.assertTrue((output / "examples/sample-poster-result-generated.json").exists())
            self.assertTrue((output / "assets/posters/2026-06-12-mexico-vs-south-africa.png").exists())
            self.assertTrue((output / "assets/posters/2026-06-12-south-korea-vs-czechia.png").exists())
            self.assertTrue((output / "assets/contact/wechat-qr.jpg").exists())
            self.assertTrue((output / "data/editions/2098/match-ledger.json").exists())
            self.assertTrue((output / "raw/体育/世界杯/2098/source-registry.json").exists())
            self.assertTrue((output / "wiki/体育/世界杯/2098/index.md").exists())
            self.assertNotIn(str(root), (output / "data/editions/2098/reports/posters/leaky-path.json").read_text(encoding="utf-8"))

    def test_profile_init_marks_missing_roster_players_blocked_instead_of_complete(self):
        init_module = load_script("worldcup_edition_init.py")
        profile_module = load_script("worldcup_profile_init.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_module.initialize_edition(root=root, edition="2098", now="2026-06-09T12:00:00+08:00")

            result = profile_module.initialize_profiles(
                root=root,
                edition="2098",
                scope=["teams", "players"],
                now="2026-06-09T12:10:00+08:00",
            )

            self.assertEqual(result["summary"]["team_dossiers"], 48)
            self.assertEqual(result["summary"]["player_dossiers"], 0)
            self.assertEqual(result["summary"]["blocked_player_profile_tasks"], 48)
            self.assertEqual(result["summary"]["source_integrity"], "partial")
            self.assertIn("player_roster_source_missing", result["blockers"])

    def test_daily_prediction_skips_started_matches_and_locks_existing_reports(self):
        init_module = load_script("worldcup_edition_init.py")
        daily_module = load_script("daily_prediction_runner.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_module.initialize_edition(root=root, edition="2098", now="2026-06-09T12:00:00+08:00")

            ledger_path = root / "_meta/projects/世界杯预测/data/editions/2098/match-ledger.json"
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            now = datetime(2026, 6, 9, 12, tzinfo=timezone.utc)
            ledger["matches"][0]["kickoff_at"] = (now + timedelta(hours=3)).isoformat()
            ledger["matches"][0]["home_team"] = {"name": "Alpha", "team_id": "alpha"}
            ledger["matches"][0]["away_team"] = {"name": "Beta", "team_id": "beta"}
            ledger["matches"][1]["kickoff_at"] = (now - timedelta(hours=1)).isoformat()
            ledger["matches"][1]["home_team"] = {"name": "Gamma", "team_id": "gamma"}
            ledger["matches"][1]["away_team"] = {"name": "Delta", "team_id": "delta"}
            ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            first = daily_module.run_daily_predictions(
                root=root,
                edition="2098",
                date="2026-06-09",
                now="2026-06-09T12:00:00+00:00",
                poster=False,
            )
            self.assertEqual(first["summary"]["predictions_created"], 1)
            self.assertEqual(first["summary"]["matches_skipped_started"], 1)
            self.assertIn("娱乐预测，非投注建议", first["disclaimer"])
            prediction = first["predictions"][0]
            self.assertLessEqual(prediction["divination_overlay"]["weight"], 0.15)
            play_card = prediction["play_card"]
            self.assertIn("share_title", play_card)
            self.assertGreaterEqual(len(play_card["watch_points"]), 2)
            self.assertIn("poster_angle", play_card)
            play_text = json.dumps(play_card, ensure_ascii=False)
            self.assertNotIn("稳胆", play_text)
            self.assertNotIn("稳赢", play_text)

            second = daily_module.run_daily_predictions(
                root=root,
                edition="2098",
                date="2026-06-09",
                now="2026-06-09T12:30:00+00:00",
                poster=False,
            )
            self.assertEqual(second["summary"]["predictions_created"], 0)
            self.assertEqual(second["summary"]["locked_existing_predictions"], 1)

    def test_poster_generator_blocks_missing_image2_backend_without_fake_success(self):
        init_module = load_script("worldcup_edition_init.py")
        daily_module = load_script("daily_prediction_runner.py")
        poster_prompt_module = load_script("poster_prompt_builder.py")
        poster_module = load_script("poster_generator.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_module.initialize_edition(root=root, edition="2098", now="2026-06-09T12:00:00+08:00")
            ledger_path = root / "_meta/projects/世界杯预测/data/editions/2098/match-ledger.json"
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            ledger["matches"][0]["kickoff_at"] = "2026-06-09T18:00:00+00:00"
            ledger["matches"][0]["home_team"] = {"name": "Alpha", "team_id": "alpha"}
            ledger["matches"][0]["away_team"] = {"name": "Beta", "team_id": "beta"}
            ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            report = daily_module.run_daily_predictions(
                root=root,
                edition="2098",
                date="2026-06-09",
                now="2026-06-09T12:00:00+00:00",
                poster=False,
            )
            manifest = poster_prompt_module.build_poster_manifest(
                root=root,
                edition="2098",
                date="2026-06-09",
                report_path=Path(report["report_path"]),
                now="2026-06-09T12:05:00+00:00",
            )
            result = poster_module.generate_posters(root=root, manifest_path=Path(manifest["manifest_path"]), backend="image2")

            self.assertEqual(result["status"], "blocked_missing_backend")
            self.assertEqual(result["summary"]["images_generated"], 0)
            self.assertTrue(Path(result["result_path"]).exists())
            self.assertIn("娱乐预测，非投注建议", manifest["poster_items"][0]["disclaimer"])

    def test_showdown_poster_prompt_uses_fixture_time_and_full_rosters(self):
        init_module = load_script("worldcup_edition_init.py")
        daily_module = load_script("daily_prediction_runner.py")
        poster_prompt_module = load_script("poster_prompt_builder.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_module.initialize_edition(root=root, edition="2098", now="2026-06-09T12:00:00+08:00")
            ledger_path = root / "_meta/projects/世界杯预测/data/editions/2098/match-ledger.json"
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            ledger["matches"][0]["kickoff_at"] = "2026-06-09T18:00:00+00:00"
            ledger["matches"][0]["home_team"] = {"name": "Alpha", "team_id": "alpha"}
            ledger["matches"][0]["away_team"] = {"name": "Beta", "team_id": "beta"}
            ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            roster_path = root / "_meta/projects/世界杯预测/data/editions/2098/rosters/fifa-squad-lists.json"
            roster_path.parent.mkdir(parents=True, exist_ok=True)
            roster_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "edition": "2098",
                        "teams": [
                            {
                                "team_id": "alpha",
                                "name": "Alpha",
                                "players": [
                                    {"shirt_number": 10, "position": "FW", "player_name": "ALPHA A"},
                                    {"shirt_number": 1, "position": "GK", "player_name": "ALPHA B"},
                                ],
                            },
                            {
                                "team_id": "beta",
                                "name": "Beta",
                                "players": [
                                    {"shirt_number": 9, "position": "FW", "player_name": "BETA A"},
                                    {"shirt_number": 4, "position": "DF", "player_name": "BETA B"},
                                ],
                            },
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            report = daily_module.run_daily_predictions(
                root=root,
                edition="2098",
                date="2026-06-09",
                now="2026-06-09T12:00:00+00:00",
                poster=False,
            )
            manifest = poster_prompt_module.build_poster_manifest(
                root=root,
                edition="2098",
                date="2026-06-09",
                report_path=Path(report["report_path"]),
                match_id="2098-GA-01",
                now="2026-06-09T12:05:00+00:00",
                style="showdown",
                timezone_name="Asia/Shanghai",
            )

            item = manifest["poster_items"][0]
            prompt = item["prompt"]
            self.assertEqual(item["style"], "showdown")
            self.assertIn("Alpha VS Beta", prompt)
            self.assertIn("6月10日 02:00 开赛", prompt)
            self.assertIn("ALPHA A", prompt)
            self.assertIn("10号 FW", prompt)
            self.assertIn("BETA B", prompt)
            self.assertIn("完整阵容", prompt)
            self.assertIn("AI 赛前预测｜胜负趋势分析", prompt)
            self.assertIn("fictional players", item["negative_prompt"])
            self.assertIn("6月10日 02:00 开赛", item["required_text"])
            prompt_text = Path(manifest["prompt_text_path"]).read_text(encoding="utf-8")
            self.assertFalse(prompt_text.lstrip().startswith("{"))
            self.assertIn("Alpha VS Beta", prompt_text)
            self.assertIn("负面提示词", prompt_text)

    def test_scoring_report_feeds_report_and_poster_prompts(self):
        init_module = load_script("worldcup_edition_init.py")
        scoring_module = load_script("prediction_scoring_model.py")
        report_prompt_module = load_script("prediction_report_prompt_builder.py")
        poster_prompt_module = load_script("poster_prompt_builder.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_module.initialize_edition(root=root, edition="2098", now="2026-06-09T12:00:00+08:00")
            ledger_path = root / "_meta/projects/世界杯预测/data/editions/2098/match-ledger.json"
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            ledger["matches"][0]["kickoff_at"] = "2026-06-09T18:00:00+00:00"
            ledger["matches"][0]["home_team"] = {"name": "Alpha", "team_id": "alpha"}
            ledger["matches"][0]["away_team"] = {"name": "Beta", "team_id": "beta"}
            ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            report = scoring_module.run_scoring_model(
                root=root,
                edition="2098",
                date="2026-06-09",
                now="2026-06-09T12:00:00+00:00",
            )
            prediction = report["predictions"][0]["prediction"]
            self.assertEqual(report["predictions"][0]["kickoff_at"], "2026-06-09T18:00:00+00:00")
            self.assertIn("score", prediction)
            self.assertIn("result", prediction)
            self.assertIn("total_goals", prediction)
            report_path = root / "_meta/projects/世界杯预测/data/editions/2098/reports/2026-06-09-prediction-report.json"

            prompt_manifest = report_prompt_module.build_report_prompt_manifest(
                root=root,
                edition="2098",
                date="2026-06-09",
                report_path=report_path,
                match_id="2098-GA-01",
                now="2026-06-09T12:05:00+00:00",
            )
            self.assertEqual(prompt_manifest["summary"]["prompt_items"], 1)
            prompt = prompt_manifest["prompt_items"][0]["prompt"]
            self.assertIn("娱乐预测，非投注建议", prompt)
            self.assertIn("禁止出现投注金额", prompt)
            self.assertTrue(Path(prompt_manifest["manifest_path"]).exists())
            self.assertTrue(Path(prompt_manifest["markdown_path"]).exists())

            poster_manifest = poster_prompt_module.build_poster_manifest(
                root=root,
                edition="2098",
                date="2026-06-09",
                report_path=report_path,
                match_id="2098-GA-01",
                now="2026-06-09T12:10:00+00:00",
            )
            self.assertEqual(poster_manifest["summary"]["poster_items"], 1)
            self.assertIn("娱乐预测，非投注建议", poster_manifest["poster_items"][0]["prompt"])
            poster_prompt_text = Path(poster_manifest["prompt_text_path"]).read_text(encoding="utf-8")
            self.assertFalse(poster_prompt_text.lstrip().startswith("{"))
            self.assertIn("Alpha vs Beta", poster_prompt_text)
            self.assertIn("娱乐预测，非投注建议", poster_prompt_text)

            team_report = scoring_module.run_scoring_model(
                root=root,
                edition="2098",
                teams=["Alpha", "Beta"],
                now="2026-06-09T12:00:00+00:00",
            )
            self.assertEqual(team_report["summary"]["predictions_created"], 1)
            self.assertEqual(team_report["filters"]["teams"], ["Alpha", "Beta"])
            self.assertTrue(
                (root / "_meta/projects/世界杯预测/data/editions/2098/reports/2026-06-09-alpha-vs-beta-prediction-report.json").exists()
            )

    def test_prediction_evidence_plan_lists_required_families_and_current_status(self):
        init_module = load_script("worldcup_edition_init.py")
        evidence_module = load_script("worldcup_prediction_evidence_planner.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_module.initialize_edition(root=root, edition="2098", now="2026-06-09T12:00:00+08:00")
            roster_path = root / "_meta/projects/世界杯预测/data/editions/2098/rosters/fifa-squad-lists.json"
            roster_path.parent.mkdir(parents=True, exist_ok=True)
            roster_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "edition": "2098",
                        "source_integrity": "complete",
                        "summary": {"teams": 48, "players": 1248, "coaches": 48},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            result = evidence_module.write_prediction_evidence_plan(
                root=root,
                edition="2098",
                now="2026-06-09T12:30:00+08:00",
            )

            by_id = {item["evidence_id"]: item for item in result["items"]}
            self.assertIn("official_fixtures", by_id)
            self.assertIn("official_rosters", by_id)
            self.assertIn("fifa_rankings", by_id)
            self.assertIn("recent_form_results", by_id)
            self.assertIn("injury_availability", by_id)
            self.assertIn("venue_rest_travel", by_id)
            self.assertEqual(by_id["official_rosters"]["status"], "complete")
            self.assertEqual(by_id["official_rosters"]["current_counts"]["players"], 1248)
            self.assertEqual(by_id["official_fixtures"]["status"], "blocked")
            self.assertIn("fixture_schedule_not_imported", by_id["official_fixtures"]["blockers"])
            self.assertEqual(by_id["fifa_rankings"]["status"], "blocked")
            self.assertIn("ranking_snapshot_missing", by_id["fifa_rankings"]["blockers"])
            self.assertEqual(result["summary"]["complete"], 1)
            self.assertTrue(Path(result["plan_path"]).exists())
            self.assertTrue(Path(result["markdown_path"]).exists())

    def test_prediction_evidence_plan_does_not_count_failed_snapshot_as_partial(self):
        init_module = load_script("worldcup_edition_init.py")
        snapshot_module = load_script("worldcup_source_snapshot_tool.py")
        evidence_module = load_script("worldcup_prediction_evidence_planner.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_module.initialize_edition(root=root, edition="2098", now="2026-06-09T12:00:00+08:00")

            snapshot_module.snapshot_source(
                root=root,
                edition="2098",
                source_id="fifa-men-ranking",
                mode="apply",
                now="2026-06-09T12:30:00+08:00",
                fetcher=lambda url: (_ for _ in ()).throw(RuntimeError("rate limit exceeded")),
            )
            result = evidence_module.write_prediction_evidence_plan(
                root=root,
                edition="2098",
                now="2026-06-09T12:40:00+08:00",
            )

            ranking = {item["evidence_id"]: item for item in result["items"]}["fifa_rankings"]
            self.assertEqual(ranking["status"], "blocked")
            self.assertIn("ranking_snapshot_fetch_failed", ranking["blockers"])
            self.assertIn("source_fetch_failed", ranking["blockers"])

    def test_github_readiness_auditor_checks_format_accuracy_and_playability(self):
        init_module = load_script("worldcup_edition_init.py")
        evidence_module = load_script("worldcup_prediction_evidence_planner.py")
        readiness_module = load_script("worldcup_github_readiness_auditor.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "scripts" / "worldcup_core.py").write_text("def build_play_card():\n    return {}\n", encoding="utf-8")
            for name in [
                "daily_prediction_runner.py",
                "prediction_report_prompt_builder.py",
                "worldcup_prediction_evidence_planner.py",
                "worldcup_source_snapshot_tool.py",
                "poster_generator.py",
            ]:
                (root / "scripts" / name).write_text("# marker\n", encoding="utf-8")
            (root / "schema").mkdir()
            for name in ["match-ledger.schema.json", "prediction-evidence-plan.schema.json", "daily-prediction-report.schema.json", "github-readiness.schema.json"]:
                schema_text = "{\"play_card\": true}\n" if name == "daily-prediction-report.schema.json" else "{}\n"
                (root / "schema" / name).write_text(schema_text, encoding="utf-8")
            (root / "skills/fifa-winner-skill").mkdir(parents=True)
            (root / "skills/fifa-winner-skill/SKILL.md").write_text(
                "Source Tiers\nPrediction Evidence\nPrediction Rules\nPoster Rules\n玩法卡片\n", encoding="utf-8"
            )
            (root / "SKILL.md").write_text("name: fifa-winner-skill\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests/test_worldcup_predictor_system.py").write_text("# marker\n", encoding="utf-8")
            (root / "README.md").write_text(
                "Quick Start\nRoadmap\nPrediction Evidence\nDaily Prediction\nGitHub Readiness\nPlayability\nExamples\nSafety\n", encoding="utf-8"
            )
            (root / "TODO.md").write_text("# Roadmap\n", encoding="utf-8")
            (root / "LICENSE").write_text("MIT License\n", encoding="utf-8")
            (root / "install_as_skill.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            (root / ".github/workflows").mkdir(parents=True)
            (root / ".github/workflows/ci.yml").write_text("name: CI\n", encoding="utf-8")
            (root / "examples").mkdir()
            for name in [
                "sample-prediction-report.json",
                "sample-poster-manifest.json",
                "sample-poster-result-blocked.json",
                "sample-poster-result-generated.json",
            ]:
                (root / "examples" / name).write_text("{}\n", encoding="utf-8")
            (root / "assets/posters").mkdir(parents=True)
            (root / "assets/contact").mkdir(parents=True)
            (root / "assets/posters/2026-06-12-mexico-vs-south-africa.png").write_bytes(b"png")
            (root / "assets/posters/2026-06-12-south-korea-vs-czechia.png").write_bytes(b"png")
            (root / "assets/contact/wechat-qr.jpg").write_bytes(b"jpg")
            (root / "pyproject.toml").write_text("[project]\nname='fifa-winner-skill'\n", encoding="utf-8")

            init_module.initialize_edition(root=root, edition="2098", now="2026-06-09T12:00:00+08:00")
            evidence_module.write_prediction_evidence_plan(root=root, edition="2098", now="2026-06-09T12:10:00+08:00")

            result = readiness_module.write_github_readiness_report(
                root=root,
                edition="2098",
                now="2026-06-09T12:20:00+08:00",
            )

            self.assertEqual(result["status"], "ready_with_known_data_gaps")
            self.assertTrue(result["summary"]["format_ready"])
            self.assertTrue(result["summary"]["data_accuracy_guardrails_ready"])
            self.assertTrue(result["summary"]["playability_ready"])
            self.assertTrue(Path(result["report_path"]).exists())
            section_ids = {section["section_id"] for section in result["sections"]}
            self.assertIn("format", section_ids)
            self.assertIn("data_accuracy", section_ids)
            self.assertIn("playability", section_ids)

    def test_evaluation_dashboard_aggregates_daily_evaluation_files(self):
        init_module = load_script("worldcup_edition_init.py")
        dashboard_module = load_script("prediction_evaluation_dashboard.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_module.initialize_edition(root=root, edition="2098", now="2026-06-09T12:00:00+08:00")
            eval_dir = root / "_meta/projects/世界杯预测/data/editions/2098/reports/evaluations"
            eval_dir.mkdir(parents=True, exist_ok=True)
            (eval_dir / "2026-06-11.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "edition": "2098",
                        "date": "2026-06-11",
                        "mode": "worldcup-prediction-post-match-evaluation",
                        "summary": {
                            "evaluated_matches": 2,
                            "result_hits": 1,
                            "score_hits": 0,
                            "total_goals_hits": 1,
                        },
                        "evaluations": [
                            {
                                "match_id": "2098-GA-01",
                                "status": "evaluated",
                                "prediction_confidence": "low",
                                "result_hit": True,
                            },
                            {
                                "match_id": "2098-GA-02",
                                "status": "evaluated",
                                "prediction_confidence": "medium",
                                "result_hit": False,
                            },
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (eval_dir / "2026-06-12.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "edition": "2098",
                        "date": "2026-06-12",
                        "mode": "worldcup-prediction-post-match-evaluation",
                        "summary": {
                            "evaluated_matches": 1,
                            "result_hits": 1,
                            "score_hits": 1,
                            "total_goals_hits": 1,
                        },
                        "evaluations": [
                            {
                                "match_id": "2098-GA-03",
                                "status": "evaluated",
                                "prediction_confidence": "medium",
                                "result_hit": True,
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            result = dashboard_module.write_evaluation_dashboard(
                root=root,
                edition="2098",
                now="2026-06-13T12:00:00+08:00",
            )

            self.assertEqual(result["status"], "written")
            self.assertEqual(result["summary"]["evaluation_days"], 2)
            self.assertEqual(result["summary"]["evaluated_matches"], 3)
            self.assertEqual(result["summary"]["result_hits"], 2)
            self.assertAlmostEqual(result["rates"]["result_hit_rate"], 2 / 3)
            calibration = result["summary"]["confidence_calibration"]
            self.assertEqual(calibration["low"]["evaluated_matches"], 1)
            self.assertEqual(calibration["low"]["result_hit_rate"], 1.0)
            self.assertEqual(calibration["medium"]["evaluated_matches"], 2)
            self.assertEqual(calibration["medium"]["result_hits"], 1)
            self.assertEqual(calibration["medium"]["result_hit_rate"], 0.5)
            self.assertTrue(Path(result["dashboard_path"]).exists())
            self.assertTrue(Path(result["markdown_path"]).exists())


if __name__ == "__main__":
    unittest.main()
