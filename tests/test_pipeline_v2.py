# -*- coding: utf-8 -*-
"""Testes automatizados do Estudio Unico Videomaker v2 (sem dependencias externas)."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import MAX_IMAGE_SECONDS, NEGATIVE_IMAGE_RULE, POSITIVE_IMAGE_RULE  # noqa: E402
from core.legacy_auditor import scan_legacy_project  # noqa: E402
from core.media_studio import (  # noqa: E402
    build_image_prompt,
    detect_split_collage,
    generate_thumbnail_variants,
    sanitize_image_prompt,
)
from core.pacing_planner import build_pacing_plan  # noqa: E402
from core.script_engine import normalize_script_records, validate_script_schema  # noqa: E402
from core.self_audit import run_final_audit  # noqa: E402
from core.video_assembler import assemble_video, export_short_9_16  # noqa: E402
from core.voice_studio import normalize_phonetics_pt, synthesize_all_scenes  # noqa: E402


def _make_sample_script(total_scenes: int = 21) -> dict:
    scenes = []
    for i in range(1, total_scenes + 1):
        act = 1 if i <= 6 else (2 if i <= 15 else 3)
        speaker = "narrador"
        if i in (2, 10, 18):
            speaker = "frida"
        elif i in (4, 12, 16):
            speaker = "luna"
        elif i == 8:
            speaker = "secundario"

        if i == 1:
            txt = (
                "A poeira dourada explodiu na pracinha e a Frida soltou um bom dia claro "
                "que deixou a Luninha paralisada no meio da grama!"
            )
        elif i == total_scenes:
            txt = (
                "Se você riu com os cães falantes hoje, deixe seu like, "
                "se inscreva no canal e mande para um amigo!"
            )
        else:
            txt = (
                f"No desafio {i}, os cães falantes correram pelo caminho de pedra da pracinha "
                "procurando os passarinhos e inventando piadas em coro antes do pôr do sol."
            )

        scenes.append({
            "scene_id": f"sc_{i:02d}",
            "act": act,
            "speaker": speaker,
            "emotion_direction": "com alegria e surpresa",
            "text": txt,
            "location": "sunny neighborhood park with green grass, stone fountain, wooden benches and blooming flowers",
            "visual_action": f"Frida and Luna reacting excitedly during step {i} near the stone fountain",
            "sfx": "whoosh_fast/crisp" if i in (1, 8, 16) else None,
            "avatar_mode": "duo" if i == 12 else (speaker if speaker in ("frida", "luna") else "none"),
        })
    return normalize_script_records({"title": "O Mistério dos Cães Falantes!", "target_minutes": 3.5, "scenes": scenes})


class TestVideomakerV2Unified(unittest.TestCase):
    def test_script_schema_and_dual_dialogue_rules(self):
        good = _make_sample_script(21)
        self.assertEqual(validate_script_schema(good), [])
        self.assertEqual(good["scenes"][3]["avatar_mode"], "luna")
        self.assertEqual(good["scenes"][11]["avatar_mode"], "duo")

        bad_greeting = _make_sample_script(21)
        bad_greeting["scenes"][0]["text"] = "Bom dia, sejam bem-vindos ao canal da Frida e da Luna!"
        self.assertTrue(any("saudacao" in e for e in validate_script_schema(bad_greeting)))

        bad_cta = _make_sample_script(21)
        bad_cta["scenes"][3]["text"] += " Deixe seu like agora!"
        self.assertTrue(any("fora da cena final" in e for e in validate_script_schema(bad_cta)))

    def test_prompt_sanitization_and_bible_injection(self):
        dirty = "CENA 1 (sc_01): BIBLIA DE CONTINUIDADE: REGRA ANTI-REPETICAO: (prioridade maxima) Frida correndo na praca!"
        clean = sanitize_image_prompt(dirty)
        for forbidden in ("CENA 1", "BIBLIA DE CONTINUIDADE", "REGRA ANTI-REPETICAO", "prioridade maxima"):
            self.assertNotIn(forbidden, clean)

        p = build_image_prompt({
            "scene_id": "sc_01",
            "speaker": "luna",
            "location": "sunny neighborhood park with stone fountain",
            "visual_action": "CENA 2: Luna barking sparkles near the fountain",
        })
        self.assertIn(POSITIVE_IMAGE_RULE, p["positive"])
        self.assertIn("sunny neighborhood park with stone fountain", p["positive"])
        self.assertIn("white pearl necklace", p["positive"])
        self.assertIn("chocolate-brown", p["positive"])
        self.assertIn("1 year old max", p["positive"])
        self.assertNotIn("CENA 2", p["positive"])
        self.assertEqual(p["negative"], NEGATIVE_IMAGE_RULE)
        self.assertIn("mature adult dogs", p["negative"])

        from core.flow_continuity import enforce_youthful_puppy_prompt
        flow_p = enforce_youthful_puppy_prompt("Frida barking near fountain")
        self.assertIn("1 year old max", flow_p)
        self.assertEqual(enforce_youthful_puppy_prompt(flow_p), flow_p)

    def test_phonetic_normalization(self):
        src = "Os cães falantes bateram as penas com a patinha e os passarinhos cantaram em coro suas piadas!"
        norm = normalize_phonetics_pt(src)
        for expected in ("cãis falantes", "pênas", "patínha", "passarínhos", "côro", "piádas"):
            self.assertIn(expected, norm)

    def test_pacing_splits_over_5s_and_thumbnails_ctr(self):
        script = _make_sample_script(24)
        timings = [
            {"scene_id": sc["scene_id"], "wav_path": f"{sc['scene_id']}.wav", "duration": 9.4 if i == 0 else 4.0}
            for i, sc in enumerate(script["scenes"])
        ]
        clips, prompts = build_pacing_plan(script, timings, gap_seconds=0.2)
        for c in clips:
            self.assertLessEqual(c["duration"], MAX_IMAGE_SECONDS + 0.05)
        sc01 = [c for c in clips if c["scene_id"] == "sc_01"]
        self.assertGreaterEqual(len(sc01), 2)
        self.assertIn("sc_01_p2", prompts)
        self.assertNotEqual(sc01[0]["ken_burns"], sc01[1]["ken_burns"])

        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            hero = td_p / "hero.jpg"
            Image.new("RGB", (1920, 1080), (220, 150, 60)).save(hero)
            thumbs = generate_thumbnail_variants(hero, td_p / "thumbs", "ELAS FALARAM?!")
            self.assertEqual(len(thumbs), 3)
            for t in thumbs:
                self.assertTrue(t.exists() and t.stat().st_size > 15000)

    def test_collage_detector(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "split.jpg"
            im = Image.new("RGB", (640, 360), (20, 40, 80))
            for x in range(320, 640):
                for y in range(360):
                    im.putpixel((x, y), (240, 200, 120))
            im.save(p)
            self.assertGreaterEqual(detect_split_collage(p), 2)

    def test_mixed_mp4_and_jpg_subclip_resolution(self):
        import subprocess
        from config import AVATAR_PROFILES, FFMPEG_EXE
        from core.video_assembler import _resolve_clip_video, render_motion_video_subclip

        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            imgs = td_p / "images"
            vids = td_p / "videos"
            imgs.mkdir()
            vids.mkdir()
            sample_vid = vids / "sc_01.mp4"
            subprocess.run(
                [FFMPEG_EXE, "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=1280x720:d=3.0",
                 "-c:v", "libx264", "-pix_fmt", "yuv420p", str(sample_vid)],
                check=True,
            )
            found = _resolve_clip_video({"clip_id": "sc_01_p1", "scene_id": "sc_01"}, imgs)
            self.assertEqual(found, sample_vid)
            self.assertIsNone(_resolve_clip_video({"clip_id": "sc_02_p1", "scene_id": "sc_02"}, imgs))
            out_seg = td_p / "seg.mp4"
            render_motion_video_subclip(sample_vid, 0.0, 2.0, out_seg, pts_factor=1.0)
            self.assertTrue(out_seg.exists() and out_seg.stat().st_size > 10000)

    def test_flow_accounts_quota_and_failover(self):
        import core.flow_accounts as fa

        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            old_cfg, old_st = fa.FLOW_ACCOUNTS_CONFIG, fa.FLOW_ACCOUNTS_STATE
            try:
                fa.FLOW_ACCOUNTS_CONFIG = td_p / "flow_accounts.json"
                fa.FLOW_ACCOUNTS_STATE = td_p / "flow_accounts_state.json"
                cfg = fa.load_accounts_config()
                self.assertEqual(len(cfg["accounts"]), 5)
                self.assertEqual([a["id"] for a in fa.get_next_available_accounts()], ["acc_1", "acc_2", "acc_3", "acc_4", "acc_5"])

                for _ in range(5):
                    fa.mark_account_usage("acc_1", credits_delta=10, email="a1@gmail.com")
                avail = [a["id"] for a in fa.get_next_available_accounts()]
                self.assertNotIn("acc_1", avail)
                self.assertEqual(avail[0], "acc_2")

                fa.mark_account_usage("acc_2", credits_delta=0, exhausted=True)
                self.assertEqual(fa.get_next_available_accounts()[0]["id"], "acc_3")
                self.assertTrue(fa.is_quota_error_text("Créditos insuficientes para gerar vídeo"))

                old_ls = fa.FLOW_LEARNED_SESSIONS
                try:
                    fa.FLOW_LEARNED_SESSIONS = td_p / "flow_learned_sessions.json"
                    fa._save_learned_sessions({"sessions": {"acc_2": {"email": "u2@gmail.com", "clicks": [{"text": "Novo projeto"}]}}})
                    loaded = fa._load_learned_sessions()
                    self.assertEqual(loaded["sessions"]["acc_2"]["email"], "u2@gmail.com")
                finally:
                    fa.FLOW_LEARNED_SESSIONS = old_ls
            finally:
                fa.FLOW_ACCOUNTS_CONFIG, fa.FLOW_ACCOUNTS_STATE = old_cfg, old_st

        fc_src = (ROOT / "core" / "flow_continuity.py").read_text(encoding="utf-8")
        self.assertNotIn("Fallback: selecionando 1a midia", fc_src)
        self.assertGreaterEqual(fc_src.count("await _wait_for_inflight_flow_generation"), 2)

    def test_e2e_unified_render_whisper_dual_avatar_and_short(self):
        """Teste real ponta a ponta: TTS + Whisper QA + Dual-Avatar + Pop ASS + 16:9 + Short 9:16."""
        tmp = Path(tempfile.mkdtemp(prefix="vm_v2_uni_"))
        try:
            mini = normalize_script_records({
                "title": "Teste Cães Falantes",
                "thumb_hook": "FALOU?!",
                "scenes": [
                    {
                        "scene_id": "sc_01", "act": 1, "speaker": "narrador",
                        "text": "Os cães falantes bateram as penas e correram pela pracinha!",
                        "location": "sunny park lawn", "visual_action": "Frida and Luna running",
                        "sfx": "whoosh_fast/crisp", "avatar_mode": "none",
                    },
                    {
                        "scene_id": "sc_02", "act": 2, "speaker": "frida",
                        "text": "Olha minha patinha! Agora eu posso pedir biscoito e contar piadas!",
                        "location": "sunny park lawn", "visual_action": "Frida smiling",
                        "sfx": "ui_pop/soft", "avatar_mode": "frida",
                    },
                    {
                        "scene_id": "sc_03", "act": 2, "speaker": "luna",
                        "text": "Os passarinhos estão cantando em coro lá no céu azul!",
                        "location": "sunny park lawn", "visual_action": "Luna looking up",
                        "sfx": None, "avatar_mode": "luna",
                    },
                    {
                        "scene_id": "sc_04", "act": 3, "speaker": "frida",
                        "text": "Que aventura incrível! Deixe seu like e se inscreva no canal!",
                        "location": "sunny park lawn", "visual_action": "Waving happily",
                        "sfx": "whoosh_fast/crisp", "avatar_mode": "frida",
                    },
                ],
            })
            audio_dir, images_dir, work_dir, out_dir = tmp / "audio", tmp / "images", tmp / "work", tmp / "output"
            images_dir.mkdir()

            timings = synthesize_all_scenes(mini, audio_dir, provider="gemini_emotion", enable_whisper_qa=True, enable_prosody_gate=False)
            self.assertEqual(len(timings), 4)
            for t in timings:
                self.assertTrue(t["qa"]["ok"], f"Whisper QA falhou em {t['scene_id']}: {t['qa']}")

            clips, _ = build_pacing_plan(mini, timings, gap_seconds=0.2)
            for idx, c in enumerate(clips):
                Image.new("RGB", (1920, 1080), (40 + idx * 25, 140, 80 + idx * 20)).save(images_dir / f"{c['clip_id']}.jpg")

            out_16_9 = out_dir / "teste_16x9.mp4"
            out_srt = out_dir / "teste.srt"
            assemble_video(clips, images_dir, work_dir, out_16_9, out_srt, with_avatar=True, burn_captions=True)
            self.assertTrue(out_16_9.exists() and out_16_9.stat().st_size > 50000)
            self.assertTrue(out_srt.exists() and len(out_srt.read_text(encoding="utf-8")) > 40)

            import core.motion_shorts as ms
            old_min = ms.SHORT_MIN_SECONDS
            ms.SHORT_MIN_SECONDS = 5.0
            try:
                short_mp4 = out_dir / "teste_short_9x16.mp4"
                export_short_9_16(out_16_9, clips, short_mp4, hook_badge="FALOU?!")
            finally:
                ms.SHORT_MIN_SECONDS = old_min
            self.assertTrue(short_mp4.exists() and short_mp4.stat().st_size > 30000)

            thumbs_dir = out_dir / "thumbs"
            generate_thumbnail_variants(images_dir / f"{clips[0]['clip_id']}.jpg", thumbs_dir, "FALOU?!")
            audit = run_final_audit(
                tmp, mini, timings, clips, images_dir, out_16_9, short_mp4, thumbs_dir, vision_check=False
            )
            non_script_issues = [x for x in audit["issues"] if not x.startswith("script:")]
            self.assertEqual(non_script_issues, [], f"Auto-auditoria detectou problemas: {non_script_issues}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_contextual_overlays_secondary_chars_and_youtube_pt_metadata(self):
        from core.video_assembler import infer_scene_overlay_style
        from core.youtube_publisher import (
            build_viral_pt_description,
            build_viral_pt_title,
            generate_viral_pt_thumbnail,
        )

        self.assertEqual(infer_scene_overlay_style({"text": "O gato Pingo dormia no cochilo"}), "zzz")
        self.assertEqual(infer_scene_overlay_style({"text": "Deu um abraço com carinho e amizade"}), "hearts")
        self.assertEqual(infer_scene_overlay_style({"text": "Os biscoitos de ossinho estavam no pote"}), "steam")
        self.assertEqual(infer_scene_overlay_style({"text": "Perto das margaridas do jardim"}), "bees")
        self.assertEqual(infer_scene_overlay_style({"text": "O pombo voou da fonte"}), "birds")
        self.assertEqual(infer_scene_overlay_style({"text": "Brilhou uma poeira dourada no ar"}), "sparkles")

        norm = normalize_script_records({
            "title": "A Aventura do Gato Pingo!",
            "secondary_characters": [{"name": "Pingo", "description": "Cute 3D Disney grey cat"}],
            "scenes": [
                {"scene_id": "sc_01", "speaker": "narrador", "text": "Frida e Pingo correram.", "location": "park", "visual_action": "Frida and Pingo"},
                {"scene_id": "sc_02", "speaker": "luna", "text": "Luna riu alto!", "location": "park", "visual_action": "Luna smiling"},
            ],
        })
        self.assertEqual(norm["secondary_characters"][0]["name"], "Pingo")
        self.assertIn("Pingo", norm["scenes"][0]["characters"])
        self.assertNotIn("Pingo", norm["scenes"][1]["characters"])

        v_title = build_viral_pt_title(norm)
        v_desc = build_viral_pt_description(norm)
        self.assertIn("Frida", v_title)
        self.assertIn("#cachorros", v_desc)
        self.assertIn("inteligência artificial", v_desc.lower())
        self.assertNotIn("#infantil", v_desc.lower())

        with tempfile.TemporaryDirectory() as td:
            hero = Path(td) / "hero.jpg"
            out_th = Path(td) / "thumb_viral_pt.jpg"
            Image.new("RGB", (1920, 1080), (240, 180, 60)).save(hero)
            generate_viral_pt_thumbnail(hero, out_th, main_hook="ELAS FALARAM?!")
            self.assertTrue(out_th.exists() and out_th.stat().st_size > 15000)

    def test_shorts_70_30_strict_mouth_sync_and_no_edge_tts(self):
        from core.motion_shorts import (
            SHORT_SPLIT_BOT_H,
            SHORT_SPLIT_TOP_H,
            SHORT_SPLIT_TOP_RATIO,
            resolve_split_avatar_states,
        )

        # Split oficial 70% topo / 30% base (1344 + 576 = 1920)
        self.assertAlmostEqual(SHORT_SPLIT_TOP_RATIO, 0.70, places=2)
        self.assertEqual(SHORT_SPLIT_TOP_H, 1344)
        self.assertEqual(SHORT_SPLIT_BOT_H, 576)

        # Sincronia labial estrita: narrador e secundarios NUNCA mexem a boca dos avatares
        self.assertEqual(resolve_split_avatar_states("narrador", 2), (False, False))
        self.assertEqual(resolve_split_avatar_states("secundario", 2), (False, False))
        self.assertEqual(resolve_split_avatar_states("gato_pingo", 2), (False, False))
        self.assertEqual(resolve_split_avatar_states("frida", 0), (False, False))
        self.assertEqual(resolve_split_avatar_states("luna", 0), (False, False))
        self.assertEqual(resolve_split_avatar_states("frida", 2), (True, False))
        self.assertEqual(resolve_split_avatar_states("luna", 1), (False, True))

        # Regra de Ouro: Edge TTS estritamente proibido
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                synthesize_all_scenes({"scenes": []}, Path(td), provider="edge")

        # Fronteiras limpas de 3 Shorts: nunca corta falas no meio e Short 03 evita o outro final
        from core.motion_shorts import select_3_short_windows
        fake_clips = []
        t_cur = 0.0
        for idx in range(12):
            dur = 12.0
            fake_clips.append({
                "clip_id": f"sc_{idx:02d}_p1",
                "scene_id": f"sc_{idx:02d}",
                "scene_audio_start": t_cur,
                "scene_audio_dur": dur - 0.3,
                "start": t_cur,
                "end": t_cur + dur,
                "speaker": "narrador",
                "sfx": None,
            })
            t_cur += dur
        wins = select_3_short_windows(fake_clips)
        self.assertEqual(len(wins), 3)
        self.assertLess(wins[2]["end"], fake_clips[-2]["start"] + 0.5)

    def test_voice_lock_story_props_at_mentions_and_veo_selection(self):
        from core.flow_continuity import _inject_at_character_mentions
        from core.media_studio import select_veo_scenes
        from core.scene_auditor import audit_voice_consistency

        # 1. Trava de vozes (Puck/Sulafat/Leda sem troca)
        ok_timings = [
            {"scene_id": "sc_01", "speaker": "narrador", "voice": "gemini-3.8-flash-tts:Puck"},
            {"scene_id": "sc_02", "speaker": "frida", "voice": "gemini-3.8-flash-tts:Sulafat"},
            {"scene_id": "sc_03", "speaker": "luna", "voice": "gemini-3.8-flash-tts:Leda"},
        ]
        self.assertEqual(audit_voice_consistency(ok_timings), [])
        bad_timings = ok_timings + [
            {"scene_id": "sc_17", "speaker": "narrador", "voice": "gemini-3.8-flash-tts:Zephyr"},
        ]
        self.assertTrue(audit_voice_consistency(bad_timings))

        # 2. Consistencia de objeto-chave por episodio (story_props) e mencao @Personagem
        norm = normalize_script_records({
            "title": "A Caminha Nova",
            "secondary_characters": [{"name": "Pipoca", "description": "Cute 3D Chihuahua puppy"}],
            "story_props": [{"name": "Caminha", "description": "Round red velvet dog bed with gold hearts"}],
            "scenes": [
                {
                    "scene_id": "sc_01", "speaker": "luna", "text": "Olha a caminha e o Pipoca!",
                    "location": "cozy living room", "visual_action": "Luna and Pipoca near the bed",
                }
            ],
        })
        self.assertEqual(norm["story_props"][0]["name"], "Caminha")
        p = build_image_prompt(
            norm["scenes"][0],
            secondary_characters=norm["secondary_characters"],
            story_props=norm["story_props"],
        )
        self.assertIn("Round red velvet dog bed with gold hearts", p["positive"])
        self.assertIn("@Pipoca", p["positive"])
        flow_txt = _inject_at_character_mentions("running in park", ["char:Frida", "char:Pipoca"])
        self.assertTrue(flow_txt.startswith("@Frida @Pipoca:"))

        # 3. Selecao de 10 cenas para Veo 3.1 Lite (8s cada)
        big_script = _make_sample_script(22)
        veo_sel = select_veo_scenes(big_script, [], target_count=10)
        self.assertEqual(len(veo_sel), 10)
        self.assertEqual(len({s["scene_id"] for s in veo_sel}), 10)

    def test_audit_fixes_breeds_selective_bible_fail_closed_and_veo_regen(self):
        import json
        from unittest import mock
        import numpy as np
        import core.legacy_auditor as legacy_auditor
        import core.scene_auditor as scene_auditor

        # 1. Validacao de racas canonicas no roteiro
        bad_breed_frida = _make_sample_script(21)
        bad_breed_frida["scenes"][1]["visual_action"] = "Frida, filhote de Golden Retriever dourada, observa a irma."
        errs_f = validate_script_schema(bad_breed_frida)
        self.assertTrue(any("Frida descrita com raca" in e for e in errs_f), errs_f)

        bad_breed_luna = _make_sample_script(21)
        bad_breed_luna["scenes"][3]["visual_action"] = "Luna, filhote de Cocker Spaniel marrom, corre no jardim."
        errs_l = validate_script_schema(bad_breed_luna)
        self.assertTrue(any("Luna descrita com raca" in e for e in errs_l), errs_l)

        good_sec = _make_sample_script(21)
        good_sec["scenes"][0]["visual_action"] = "Frida e Luna observam o chihuahua Pipoca pular na grama."
        self.assertEqual(validate_script_schema(good_sec), [])

        # 2. Character Bible seletiva: nao injeta Frida/Luna quando cena tem apenas personagem secundario
        p_sec_only = build_image_prompt(
            {
                "scene_id": "sc_04",
                "speaker": "narrador",
                "text": "O Juiz Bigodes sopra o apito.",
                "location": "judge tower",
                "visual_action": "Juiz Bigodes blows a golden whistle",
                "characters": ["Juiz Bigodes"],
            },
            secondary_characters=[{"name": "Juiz Bigodes", "description": "Fluffy gray Persian cat with monocle"}],
        )
        self.assertIn("@Juiz Bigodes", p_sec_only["positive"])
        self.assertNotIn("English bulldog puppy", p_sec_only["positive"])
        self.assertNotIn("dachshund puppy", p_sec_only["positive"])

        # 3. Vision QA fail-closed em strict_vision=True e legacy_auditor checando matches_action
        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            dummy_jpg = td_p / "frame.jpg"
            arr = np.full((360, 640, 3), 140, dtype=np.uint8)
            Image.fromarray(arr).save(dummy_jpg, quality=92)

            with mock.patch.object(scene_auditor, "_get_google_keys", return_value=[]):
                res_strict = scene_auditor.audit_scene_visual_with_vision(
                    [dummy_jpg], {"scene_id": "sc_01", "text": "teste", "location": "park", "visual_action": "run"},
                    strict_vision=True,
                    audit_profile="strict",
                )
                self.assertFalse(res_strict["ok"])
                self.assertTrue(res_strict.get("vision_unavailable"))

            fake_resp = mock.MagicMock()
            fake_resp.__enter__.return_value = fake_resp
            fake_resp.read.return_value = json.dumps({
                "candidates": [{"content": {"parts": [{"text": json.dumps({
                    "matches_location": True,
                    "matches_action": False,
                    "has_collage_or_split": False,
                    "has_visible_text": False,
                    "reason": "acao errada",
                })}]}}]
            }).encode("utf-8")
            with mock.patch.object(legacy_auditor, "_get_google_keys", return_value=["k1"]), \
                 mock.patch("urllib.request.urlopen", return_value=fake_resp):
                leg_res = legacy_auditor.audit_image_with_vision(
                    dummy_jpg, "park", "Luna jumps", expected_narration="Luna pula", fail_closed=True,
                )
                self.assertFalse(leg_res["ok"])

        # 4. generate_and_audit_scenes: regeneracao de Veo reprovado, stills de _p2 e ancoragem por prop
        with tempfile.TemporaryDirectory() as td:
            proj = Path(td)
            imgs_dir = proj / "assets" / "images"
            vids_dir = proj / "assets" / "videos"
            (proj / "artifacts").mkdir(parents=True, exist_ok=True)

            script = {
                "title": "Teste Props",
                "story_props": [{"name": "Caminha", "description": "Red velvet dog bed"}],
                "scenes": [
                    {
                        "scene_id": "sc_01", "act": 1, "speaker": "narrador",
                        "text": "Frida corre no quintal verde!",
                        "location": "green yard", "visual_action": "Frida runs on grass",
                        "characters": ["Frida"],
                    },
                    {
                        "scene_id": "sc_02", "act": 2, "speaker": "luna",
                        "text": "Olha a Caminha nova na sala!",
                        "location": "living room", "visual_action": "Luna looks at Caminha",
                        "characters": ["Luna"],
                    },
                ],
            }
            vclips = [
                {"clip_id": "sc_01_p1", "scene_id": "sc_01", "prompt_variant": "main"},
                {"clip_id": "sc_01_p2", "scene_id": "sc_01", "prompt_variant": "reaction"},
                {"clip_id": "sc_02_p1", "scene_id": "sc_02", "prompt_variant": "main"},
            ]
            prompts = {
                "sc_01_p1": build_image_prompt(script["scenes"][0], story_props=script["story_props"]),
                "sc_02_p1": build_image_prompt(script["scenes"][1], story_props=script["story_props"]),
            }

            rng = np.random.default_rng(7)
            noise_rgb = rng.integers(60, 200, (360, 640, 3), dtype=np.uint8)

            def _fake_save_img(dst: Path):
                dst.parent.mkdir(parents=True, exist_ok=True)
                Image.fromarray(noise_rgb).save(dst, quality=92)

            img_calls: list[str] = []
            anchor_calls: list[tuple[str, bool]] = []
            veo_attempts = {"sc_01": 0}

            def _fake_gen_img(prompt, out_path, **kwargs):
                img_calls.append(out_path.name)
                _fake_save_img(out_path)
                return out_path

            def _fake_gen_veo(scene, images_dir, videos_dir, script_data, **kwargs):
                sid = scene["scene_id"]
                veo_attempts[sid] = veo_attempts.get(sid, 0) + 1
                mp4 = videos_dir / f"{sid}.mp4"
                mp4.parent.mkdir(parents=True, exist_ok=True)
                mp4.write_bytes(b"\x00" * 60000)
                return {"ok": True, "path": str(mp4), "account_id": "acc_1", "elapsed_s": 1.0}

            def _fake_audit_vis(frames, scene, **kwargs):
                anchor_calls.append((scene["scene_id"], kwargs.get("anchor_prop_image") is not None))
                if any(f.name.startswith("sc_01_f") for f in frames) and veo_attempts["sc_01"] == 1:
                    return {"checked": True, "ok": False, "reason": "veo tentativa 1 errada", "fix_prompt_hint": "fix action"}
                return {"checked": True, "ok": True, "reason": "OK"}

            def _fake_kf(v_mp4, out_dir, prefix, count=3):
                kf = out_dir / f"{prefix}_f1.jpg"
                _fake_save_img(kf)
                return [kf]

            def _fake_stills(v_mp4, sc_clips, images_dir):
                for c in sc_clips[1:]:
                    _fake_save_img(images_dir / f"{c['clip_id']}.jpg")

            with mock.patch.object(scene_auditor, "generate_single_image", side_effect=_fake_gen_img), \
                 mock.patch.object(scene_auditor, "generate_single_veo_video", side_effect=_fake_gen_veo), \
                 mock.patch.object(scene_auditor, "audit_scene_visual_with_vision", side_effect=_fake_audit_vis), \
                 mock.patch.object(scene_auditor, "_extract_video_keyframes", side_effect=_fake_kf), \
                 mock.patch.object(scene_auditor, "_extract_stills_for_veo_subclips", side_effect=_fake_stills):
                rep = scene_auditor.generate_and_audit_scenes(
                    proj_dir=proj,
                    script_data=script,
                    visual_clips=vclips,
                    prompts_manifest=prompts,
                    images_dir=imgs_dir,
                    videos_dir=vids_dir,
                    veo_scene_ids={"sc_01"},
                    generate_veo_inline=True,
                    veo_max_retries=2,
                    strict_vision=True,
                )

            self.assertTrue(rep["approved"], rep)
            self.assertEqual(veo_attempts["sc_01"], 2)
            self.assertNotIn("sc_01_p2.jpg", img_calls)
            self.assertTrue((imgs_dir / "sc_01_p2.jpg").exists())
            # sc_01 nao menciona Caminha -> nao cria ancora de Caminha, logo sc_02 nao herda sc_01_p1 como ancora
            self.assertFalse(any(has_anc for _, has_anc in anchor_calls))

            # 5. run_final_audit deve reprovar se min_veo_videos=10 e pasta videos estiver vazia
            vids_dir.joinpath("sc_01.mp4").unlink(missing_ok=True)
            fa = run_final_audit(
                proj_dir=proj,
                script_data=_make_sample_script(21),
                tts_timings=[],
                visual_clips=[],
                images_dir=imgs_dir,
                out_16_9=proj / "missing_16x9.mp4",
                out_short=None,
                thumbs_dir=proj / "thumbs",
                min_veo_videos=10,
            )
            self.assertFalse(fa["approved"])
            self.assertTrue(any("veo:" in iss for iss in fa["issues"]), fa["issues"])

    def test_chirp3_hd_voice_lock_quota_guard_and_payload(self):
        import base64
        import json
        from unittest import mock
        import core.voice_studio as vs
        from core.scene_auditor import audit_voice_consistency

        captured: dict[str, object] = {}

        class _FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return json.dumps({"audioContent": base64.b64encode(b"ID3FAKECHIRP").decode("ascii")}).encode("utf-8")

        def _fake_urlopen(req, timeout=45):
            captured["url"] = req.full_url
            captured["headers"] = {k.lower(): v for k, v in req.header_items()}
            captured["payload"] = json.loads(req.data.decode("utf-8"))
            return _FakeResp()

        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            fake_cred = td_p / "sa.json"
            fake_cred.write_text('{"type":"service_account"}', encoding="utf-8")
            usage_file = td_p / "chirp3_usage.json"
            out_mp3 = td_p / "frida.mp3"

            with mock.patch.object(vs, "resolve_chirp3_credentials_path", return_value=fake_cred), \
                 mock.patch.object(vs, "_get_chirp3_access_token", return_value="tok_oauth2_test"), \
                 mock.patch("urllib.request.urlopen", side_effect=_fake_urlopen):
                used_v, mode = vs._synthesize_chirp3_hd("Olá Frida!", "frida", out_mp3, state_file=usage_file)

            self.assertEqual(used_v, "chirp3_hd:pt-BR-Chirp3-HD-Sulafat")
            self.assertEqual(mode, "chirp3_hd")
            self.assertTrue(out_mp3.exists())
            self.assertEqual(captured["url"], "https://texttospeech.googleapis.com/v1/text:synthesize")
            self.assertEqual(captured["headers"]["authorization"], "Bearer tok_oauth2_test")
            payload = captured["payload"]
            self.assertEqual(payload["voice"], {"languageCode": "pt-BR", "name": "pt-BR-Chirp3-HD-Sulafat"})
            self.assertNotIn("modelName", payload)

            st = json.loads(usage_file.read_text(encoding="utf-8"))
            self.assertEqual(st["chars_used"], len("Olá Frida!"))
            with self.assertRaises(RuntimeError) as ctx:
                vs._consume_chirp3_chars(100, state_file=usage_file, limit=len("Olá Frida!") + 10)
            self.assertIn("TRAVA DE CUSTO CHIRP 3 HD", str(ctx.exception))

            # Testa também autenticacao via OAuth 2.0 Desktop (token JSON + x-goog-user-project)
            oauth_tok = td_p / "cloud_tts_token.json"
            oauth_tok.write_text('{"token":"tok_user_oauth","refresh_token":"r1"}', encoding="utf-8")
            fake_creds_obj = mock.MagicMock(valid=True, token="tok_user_oauth", quota_project_id="")
            out_nar = td_p / "narrador.mp3"
            with mock.patch.object(vs, "resolve_chirp3_credentials_path", return_value=None), \
                 mock.patch("google.oauth2.credentials.Credentials.from_authorized_user_file", return_value=fake_creds_obj), \
                 mock.patch.object(vs, "resolve_chirp3_oauth_paths", return_value=(None, oauth_tok, "ingles-514519")), \
                 mock.patch("urllib.request.urlopen", side_effect=_fake_urlopen):
                used_n, _ = vs._synthesize_chirp3_hd("Narracao teste", "narrador", out_nar, state_file=usage_file, token_path=oauth_tok)
            self.assertEqual(used_n, "chirp3_hd:pt-BR-Chirp3-HD-Puck")
            self.assertEqual(captured["headers"]["authorization"], "Bearer tok_user_oauth")
            self.assertEqual(captured["headers"]["x-goog-user-project"], "ingles-514519")
            self.assertEqual(captured["payload"]["voice"]["name"], "pt-BR-Chirp3-HD-Puck")

        # audit_voice_consistency aceita Chirp 3 HD travado e reprova troca de voz
        self.assertEqual(
            audit_voice_consistency([
                {"scene_id": "sc_01", "speaker": "narrador", "voice": "chirp3_hd:pt-BR-Chirp3-HD-Puck"},
                {"scene_id": "sc_02", "speaker": "frida", "voice": "chirp3_hd:pt-BR-Chirp3-HD-Sulafat"},
                {"scene_id": "sc_03", "speaker": "luna", "voice": "chirp3_hd:pt-BR-Chirp3-HD-Leda"},
            ]),
            [],
        )
        self.assertTrue(
            audit_voice_consistency([
                {"scene_id": "sc_01", "speaker": "narrador", "voice": "chirp3_hd:pt-BR-Chirp3-HD-Zephyr"},
            ])
        )
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                synthesize_all_scenes({"scenes": []}, Path(td), provider="edge")

    def test_story_props_as_flow_characters_and_whisper_audio_vision_audit(self):
        import asyncio
        from unittest import mock
        import core.flow_accounts as fa
        import core.scene_auditor as sa

        with tempfile.TemporaryDirectory() as td:
            td_p = Path(td)
            img = td_p / "big.jpg"
            Image.new("RGB", (1920, 1080), (180, 40, 40)).save(img)
            b64 = sa._encode_vision_jpeg_b64(img, max_w=960)
            self.assertTrue(len(b64) > 100)

            created_calls: list[str] = []

            async def _fake_ensure_all(_pg, _url):
                return {"Frida": True, "Luna": True}

            async def _fake_check(_pg, required=()):
                return {r: False for r in required}

            async def _fake_gen_img(_pg, prompt, out_jpg, **_kw):
                Image.new("RGB", (640, 640), (200, 30, 30)).save(out_jpg)
                return {"ok": True}

            async def _fake_create_char(_pg, name, _portrait, _desc, _url):
                created_calls.append(name)
                return True

            with mock.patch.object(fa, "ensure_all_characters_created", side_effect=_fake_ensure_all), \
                 mock.patch.object(fa, "check_characters_present", side_effect=_fake_check), \
                 mock.patch.object(fa, "generate_flow_image", side_effect=_fake_gen_img), \
                 mock.patch.object(fa, "create_character_in_flow", side_effect=_fake_create_char):
                res = asyncio.run(
                    fa.ensure_story_characters_created(
                        None,
                        {
                            "secondary_characters": [{"name": "Pipoca", "description": "Cute Chihuahua"}],
                            "story_props": [{"name": "Caminha_Real", "description": "Red velvet bed with gold hearts"}],
                        },
                        "https://flow.google.com/project/demo",
                        portrait_dir=td_p / "chars",
                    )
                )
            self.assertTrue(res.get("Pipoca"))
            self.assertTrue(res.get("Caminha_Real"))
            self.assertEqual(created_calls, ["Pipoca", "Caminha_Real"])

            # Verifica que audio_heard_pt (Whisper) entra no prompt do auditor
            captured_prompts: list[str] = []

            class _Resp:
                def __enter__(self):
                    return self
                def __exit__(self, *a):
                    return False
                def read(self):
                    import json as _json
                    return _json.dumps({
                        "candidates": [{"content": {"parts": [{"text": _json.dumps({
                            "matches_narration": True, "matches_location": True,
                            "matches_characters": True, "matches_story_props": True,
                            "has_collage_or_split": False, "has_visible_text": False,
                            "reason": "ok", "fix_prompt_hint": ""
                        })}]}}]
                    }).encode("utf-8")

            def _fake_urlopen(req, timeout=28):
                import json as _json
                body = _json.loads(req.data.decode("utf-8"))
                captured_prompts.append(body["contents"][0]["parts"][0]["text"])
                return _Resp()

            with mock.patch.object(sa, "_get_google_keys", return_value=["DUMMY_TEST_KEY_FOR_MOCK"]), \
                 mock.patch("urllib.request.urlopen", side_effect=_fake_urlopen):
                vis = sa.audit_scene_visual_with_vision(
                    [img],
                    {"scene_id": "sc_01", "text": "Olha a caminha!", "location": "sala", "visual_action": "Luna olha a caminha"},
                    audio_heard_pt="Olha a caminha vermelha!",
                )
            self.assertTrue(vis["ok"])
            self.assertIn("Actual Audio Heard in WAV", captured_prompts[0])
            self.assertIn("Olha a caminha vermelha!", captured_prompts[0])

    def test_audit_fixes_v2_veo_vision_unavail_acc5_credits_and_at_strip(self):
        from unittest import mock
        import numpy as np
        import core.flow_accounts as fa
        import core.scene_auditor as sa

        # 1. Strip @ apenas no campo 'text' falado, preservando @Nome em visual_action
        norm = normalize_script_records({
            "title": "Teste Arroba",
            "story_props": [{"name": "Almofada Rosa", "description": "Pink plush cushion"}],
            "scenes": [{
                "scene_id": "sc_01",
                "speaker": "luna",
                "text": "Olha a @Almofada Rosa e o @Pipoca!",
                "location": "sala",
                "visual_action": "Luna pula na @Almofada Rosa perto de @Pipoca",
            }],
        })
        self.assertEqual(norm["scenes"][0]["text"], "Olha a Almofada Rosa e o Pipoca!")
        self.assertIn("@Almofada Rosa", norm["scenes"][0]["visual_action"])

        # 2. Suporte a max_credits por conta (acc_5 = 1050 creditos)
        fake_cfg = {
            "max_credits_per_account_per_day": 50,
            "credits_per_veo_lite_8s": 10,
            "accounts": [
                {"id": "acc_1", "enabled": True},
                {"id": "acc_5", "enabled": True, "max_credits": 1050},
            ],
        }
        fake_state = {
            "date": "2026-11-21",
            "accounts": {
                "acc_1": {"credits_used_today": 50, "exhausted_today": False},
                "acc_5": {"credits_used_today": 80, "exhausted_today": False},
            },
        }
        with mock.patch.object(fa, "load_accounts_config", return_value=fake_cfg), \
             mock.patch.object(fa, "load_accounts_state", return_value=fake_state):
            avail = fa.get_next_available_accounts()
        self.assertEqual([a["id"] for a in avail], ["acc_5"])

        # 3. vision_unavailable nao apaga video Veo existente no disco
        with tempfile.TemporaryDirectory() as td:
            proj = Path(td)
            imgs_dir = proj / "assets" / "images"
            vids_dir = proj / "assets" / "videos"
            imgs_dir.mkdir(parents=True, exist_ok=True)
            vids_dir.mkdir(parents=True, exist_ok=True)
            (proj / "artifacts").mkdir(parents=True, exist_ok=True)

            rng = np.random.default_rng(11)
            arr = rng.integers(50, 210, (360, 640, 3), dtype=np.uint8)
            Image.fromarray(arr).save(imgs_dir / "sc_01_p1.jpg", quality=92)
            v_mp4 = vids_dir / "sc_01.mp4"
            v_mp4.write_bytes(b"\x01" * 70000)

            script = {
                "title": "Preserva Veo",
                "scenes": [{
                    "scene_id": "sc_01", "act": 1, "speaker": "narrador",
                    "text": "Frida brinca no jardim!", "location": "garden",
                    "visual_action": "Frida plays in garden", "characters": ["Frida"],
                }],
            }
            vclips = [{"clip_id": "sc_01_p1", "scene_id": "sc_01", "prompt_variant": "main"}]
            prompts = {"sc_01_p1": {"positive": "test", "negative": "test"}}

            def _fake_vis(frames, scene, **kwargs):
                if any("sc_01_f" in p.name or "frame" in p.name for p in frames):
                    return {"checked": False, "ok": False, "vision_unavailable": True, "reason": "429"}
                return {"checked": True, "ok": True, "reason": "OK"}

            def _fake_kf(mp4, out_dir, prefix, count=3):
                kf = out_dir / f"{prefix}_f1.jpg"
                Image.fromarray(arr).save(kf, quality=92)
                return [kf]

            def _fake_gen_img(prompt, out_path, **kwargs):
                Image.fromarray(arr).save(out_path, quality=92)
                return out_path

            with mock.patch.object(sa, "generate_single_image", side_effect=_fake_gen_img), \
                 mock.patch.object(sa, "audit_scene_visual_with_vision", side_effect=_fake_vis), \
                 mock.patch.object(sa, "_extract_video_keyframes", side_effect=_fake_kf), \
                 mock.patch.object(sa.time, "sleep"):
                rep = sa.generate_and_audit_scenes(
                    proj_dir=proj,
                    script_data=script,
                    visual_clips=vclips,
                    prompts_manifest=prompts,
                    images_dir=imgs_dir,
                    videos_dir=vids_dir,
                    veo_scene_ids={"sc_01"},
                    generate_veo_inline=False,
                    auto_fix=True,
                    veo_max_retries=2,
                    strict_vision=True,
                    stop_on_scene_failure=True,
                )
            self.assertFalse(rep["approved"])
            self.assertTrue(v_mp4.exists(), "vision_unavailable nao pode apagar .mp4 existente!")

    def test_video_collage_false_positive_immunity_and_persistent_audit_cache(self):
        import json as _json
        from unittest import mock
        import numpy as np
        import core.scene_auditor as sa

        with tempfile.TemporaryDirectory() as td:
            proj = Path(td)
            imgs_dir = proj / "assets" / "images"
            vids_dir = proj / "assets" / "videos"
            imgs_dir.mkdir(parents=True, exist_ok=True)
            vids_dir.mkdir(parents=True, exist_ok=True)
            (proj / "artifacts").mkdir(parents=True, exist_ok=True)

            rng = np.random.default_rng(29)
            arr1 = rng.integers(50, 210, (360, 640, 3), dtype=np.uint8)
            arr2 = rng.integers(50, 210, (360, 640, 3), dtype=np.uint8)
            f1 = imgs_dir / "sc_06_p1.jpg"
            f2 = imgs_dir / "sc_06_kf2.jpg"
            Image.fromarray(arr1).save(f1, quality=92)
            Image.fromarray(arr2).save(f2, quality=92)
            v_mp4 = vids_dir / "sc_06.mp4"
            v_mp4.write_bytes(b"\x02" * 70000)

            # 1. LLM devolvendo has_collage_or_split=True para frames sequenciais de video NAO pode reprovar video,
            #    mas DEVE reprovar quando for uma unica imagem estatica.
            captured_prompts: list[str] = []

            class _RespCollage:
                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False

                def read(self):
                    return _json.dumps({
                        "candidates": [{"content": {"parts": [{"text": _json.dumps({
                            "matches_narration": True,
                            "matches_location": True,
                            "matches_characters": True,
                            "matches_story_props": True,
                            "has_collage_or_split": True,
                            "has_visible_text": False,
                            "reason": "quadros sequenciais",
                            "fix_prompt_hint": "",
                        })}]}}]
                    }).encode("utf-8")

            def _fake_urlopen(req, timeout=28):
                body = _json.loads(req.data.decode("utf-8"))
                captured_prompts.append(body["contents"][0]["parts"][0]["text"])
                return _RespCollage()

            scene_sample = {
                "scene_id": "sc_06",
                "act": 1,
                "speaker": "frida",
                "text": "A bolinha caiu certinho no meio da caminha.",
                "location": "sala",
                "visual_action": "Bolinha verde na @Caminha_Real",
                "characters": ["Frida"],
            }
            with mock.patch.object(sa, "_get_google_keys", return_value=["DUMMY_TEST_KEY"]), \
                 mock.patch("urllib.request.urlopen", side_effect=_fake_urlopen):
                vid_res = sa.audit_scene_visual_with_vision([f1, f2], scene_sample, is_video_keyframes=True)
                img_res = sa.audit_scene_visual_with_vision([f1], scene_sample, is_video_keyframes=False)

            self.assertTrue(vid_res["ok"], vid_res)
            self.assertFalse(vid_res["has_collage_or_split"])
            self.assertIn("VIDEO KEYFRAMES AUDIT", captured_prompts[0])
            self.assertFalse(img_res["ok"])
            self.assertTrue(img_res["has_collage_or_split"])

            # 2. Cache persistente pula re-auditoria quando midia e roteiro nao mudam, e invalida ao mudar texto
            vision_calls = {"count": 0}

            def _fake_audit_ok(frames, sc, **kwargs):
                vision_calls["count"] += 1
                return {"checked": True, "ok": True, "reason": "OK"}

            def _fake_kf(mp4, out_dir, prefix, count=3):
                kf = out_dir / f"{prefix}_f1.jpg"
                Image.fromarray(arr1).save(kf, quality=92)
                return [kf]

            script = {"title": "Cache", "scenes": [dict(scene_sample)]}
            vclips = [{"clip_id": "sc_06_p1", "scene_id": "sc_06", "prompt_variant": "main"}]
            prompts = {"sc_06_p1": {"positive": "test", "negative": "test"}}

            with mock.patch.object(sa, "audit_scene_visual_with_vision", side_effect=_fake_audit_ok), \
                 mock.patch.object(sa, "_extract_video_keyframes", side_effect=_fake_kf):
                rep1 = sa.generate_and_audit_scenes(
                    proj_dir=proj,
                    script_data=script,
                    visual_clips=vclips,
                    prompts_manifest=prompts,
                    images_dir=imgs_dir,
                    videos_dir=vids_dir,
                    veo_scene_ids={"sc_06"},
                    generate_veo_inline=False,
                    strict_vision=True,
                )
                self.assertTrue(rep1["approved"])
                self.assertEqual(vision_calls["count"], 2)  # 1 imagem + 1 video

                rep2 = sa.generate_and_audit_scenes(
                    proj_dir=proj,
                    script_data=script,
                    visual_clips=vclips,
                    prompts_manifest=prompts,
                    images_dir=imgs_dir,
                    videos_dir=vids_dir,
                    veo_scene_ids={"sc_06"},
                    generate_veo_inline=False,
                    strict_vision=True,
                )
                self.assertTrue(rep2["approved"])
                self.assertEqual(vision_calls["count"], 2)  # Zero novas chamadas!

                # Alterou texto da narracao -> cache deve invalidar e re-auditar
                script["scenes"][0]["text"] = "Novo texto alterado na cena seis!"
                rep3 = sa.generate_and_audit_scenes(
                    proj_dir=proj,
                    script_data=script,
                    visual_clips=vclips,
                    prompts_manifest=prompts,
                    images_dir=imgs_dir,
                    videos_dir=vids_dir,
                    veo_scene_ids={"sc_06"},
                    generate_veo_inline=False,
                    strict_vision=True,
                )
                self.assertTrue(rep3["approved"])
                self.assertEqual(vision_calls["count"], 4)

    def test_veo_anti_waste_archive_cap_and_per_scene_secondary_chars(self):
        from unittest import mock
        import numpy as np
        import core.scene_auditor as sa

        # 1. Filtro por cena de secondary_characters (Pipoca nao vaza em sc_01)
        sec_all = [{"name": "Pipoca", "description": "Cute Chihuahua"}]
        sc_01 = {"scene_id": "sc_01", "text": "Frida e Luna correm.", "visual_action": "Corrida", "characters": ["Frida", "Luna"]}
        sc_04 = {"scene_id": "sc_04", "text": "Pipoca pula!", "visual_action": "Salto", "characters": ["Frida", "Luna", "Pipoca"]}
        self.assertEqual(sa._scene_matching_secondary_chars(sc_01, sec_all), [])
        self.assertEqual([c["name"] for c in sa._scene_matching_secondary_chars(sc_04, sec_all)], ["Pipoca"])

        # 2. Cap de 1 nova geracao Veo paga por cena + arquivamento (nao deleta MP4 reprovado)
        with tempfile.TemporaryDirectory() as td:
            proj = Path(td)
            imgs_dir = proj / "assets" / "images"
            vids_dir = proj / "assets" / "videos"
            imgs_dir.mkdir(parents=True, exist_ok=True)
            vids_dir.mkdir(parents=True, exist_ok=True)
            (proj / "artifacts").mkdir(parents=True, exist_ok=True)

            rng = np.random.default_rng(42)
            arr = rng.integers(50, 210, (360, 640, 3), dtype=np.uint8)
            Image.fromarray(arr).save(imgs_dir / "sc_01_p1.jpg", quality=92)

            script = {
                "title": "Anti Waste",
                "secondary_characters": sec_all,
                "scenes": [{
                    "scene_id": "sc_01", "act": 1, "speaker": "narrador",
                    "text": "A largada comecou!", "location": "pista",
                    "visual_action": "Varios caes correndo com Frida e Luna",
                    "characters": ["Frida", "Luna"],
                }],
            }
            vclips = [{"clip_id": "sc_01_p1", "scene_id": "sc_01", "prompt_variant": "main"}]
            prompts = {"sc_01_p1": {"positive": "test", "negative": "test"}}
            veo_gen_calls = {"count": 0}
            seen_sec_in_vision: list[list[dict[str, str]] | None] = []

            def _fake_veo(scene, images_dir, videos_dir, script_data, **kwargs):
                veo_gen_calls["count"] += 1
                mp4 = videos_dir / f"{scene['scene_id']}.mp4"
                mp4.write_bytes(b"\x03" * 80000)
                return {"ok": True, "path": str(mp4), "account_id": "acc_5"}

            def _fake_vis(frames, sc, **kwargs):
                seen_sec_in_vision.append(kwargs.get("secondary_characters"))
                if any("sc_01_f" in p.name for p in frames):
                    return {"checked": True, "ok": False, "reason": "objeto extra"}
                return {"checked": True, "ok": True, "reason": "OK"}

            def _fake_kf(mp4, out_dir, prefix, count=3):
                kf = out_dir / f"{prefix}_f1.jpg"
                Image.fromarray(arr).save(kf, quality=92)
                return [kf]

            with mock.patch.object(sa, "generate_single_veo_video", side_effect=_fake_veo), \
                 mock.patch.object(sa, "audit_scene_visual_with_vision", side_effect=_fake_vis), \
                 mock.patch.object(sa, "_extract_video_keyframes", side_effect=_fake_kf):
                rep = sa.generate_and_audit_scenes(
                    proj_dir=proj,
                    script_data=script,
                    visual_clips=vclips,
                    prompts_manifest=prompts,
                    images_dir=imgs_dir,
                    videos_dir=vids_dir,
                    veo_scene_ids={"sc_01"},
                    generate_veo_inline=True,
                    veo_max_retries=3,
                    max_new_veo_per_scene=1,
                    strict_vision=True,
                    stop_on_scene_failure=True,
                )
            self.assertFalse(rep["approved"])
            self.assertEqual(veo_gen_calls["count"], 1, "Nao pode regenerar mais de 1 Veo pago na mesma cena!")
            archived = list((vids_dir / "_archive").glob("sc_01_*.mp4"))
            self.assertEqual(len(archived), 1, "Video reprovado deve ir para _archive e nao ser apagado!")
            self.assertTrue(all(x == [] for x in seen_sec_in_vision))

    def test_veo_ledger_1_per_scene_lock_and_multi_video_scene_montage(self):
        import json as _json
        import subprocess
        from unittest import mock
        from config import FFMPEG_EXE, MAX_VEO_GENERATIONS_PER_SCENE
        import core.flow_accounts as fa
        import core.media_studio as ms
        import core.video_assembler as va
        from core.voice_studio import probe_duration

        self.assertEqual(MAX_VEO_GENERATIONS_PER_SCENE, 1)

        with tempfile.TemporaryDirectory() as td:
            proj = Path(td)
            imgs_dir = proj / "assets" / "images"
            vids_dir = proj / "assets" / "videos"
            imgs_dir.mkdir(parents=True, exist_ok=True)
            vids_dir.mkdir(parents=True, exist_ok=True)
            (proj / "artifacts").mkdir(parents=True, exist_ok=True)

            # 1. Ledger bloqueia 2a geracao paga na mesma cena mesmo se o arquivo foi arquivado/removido
            src_dummy = vids_dir / "_src_valid.mp4"
            subprocess.run(
                [FFMPEG_EXE, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=640x360:d=2.5",
                 "-c:v", "libx264", "-preset", "ultrafast", str(src_dummy)],
                check=True,
            )
            while src_dummy.stat().st_size < 55_000:
                src_dummy.write_bytes(src_dummy.read_bytes() + b"\x00" * 55_000)

            async def _fake_failover(**kwargs):
                dst = Path(kwargs["out_mp4"])
                dst.write_bytes(src_dummy.read_bytes())
                return {"ok": True, "path": str(dst), "account_id": "acc_5"}

            sc1 = {"scene_id": "sc_01", "text": "Largada!", "location": "pista", "visual_action": "Corrida", "characters": ["Frida"]}
            sc2 = {"scene_id": "sc_02", "text": "Luna corre!", "location": "pista", "visual_action": "Luna corre", "characters": ["Luna"]}
            script = {"title": "Ledger", "scenes": [sc1, sc2]}

            with mock.patch.object(fa, "generate_video_with_failover", side_effect=_fake_failover):
                ms.generate_single_veo_video(sc1, imgs_dir, vids_dir, script, proj_dir=proj, force=True)
                ledger = _json.loads((proj / "artifacts" / "veo_generation_ledger.json").read_text(encoding="utf-8"))
                self.assertEqual(ledger["scenes"]["sc_01"][0]["status"], "downloaded")

                # Arquiva/remove sc_01.mp4 -> 2a tentativa forçada deve bater no TRAVA-VEO-CENA!
                (vids_dir / "sc_01.mp4").unlink()
                with self.assertRaises(RuntimeError) as ctx:
                    ms.generate_single_veo_video(sc1, imgs_dir, vids_dir, script, proj_dir=proj, force=True)
                self.assertIn("TRAVA-VEO-CENA", str(ctx.exception))

                # Outra cena distinta (sc_02) e allow_extra_veo=True funcionam normalmente
                ms.generate_single_veo_video(sc2, imgs_dir, vids_dir, script, proj_dir=proj, force=True)
                ms.generate_single_veo_video(sc1, imgs_dir, vids_dir, script, proj_dir=proj, force=True, allow_extra_veo=True)

            # 2. _resolve_scene_videos + render_multi_video_montage_subclip combinam multiplos videos da mesma cena
            src_dummy.unlink(missing_ok=True)
            (vids_dir / "sc_02.mp4").unlink(missing_ok=True)
            colors = ("red", "green", "yellow")
            for name, col in zip(("sc_01.mp4", "sc_01_v2.mp4", "sc_01_v3.mp4"), colors):
                p = vids_dir / name
                subprocess.run(
                    [FFMPEG_EXE, "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c={col}:s=640x360:d=2.2",
                     "-c:v", "libx264", "-preset", "ultrafast", str(p)],
                    check=True,
                )
                if p.stat().st_size <= 50_000:
                    p.write_bytes(p.read_bytes() + b"\x00" * 52_000)

            found_vids = va._resolve_scene_videos("sc_01", imgs_dir)
            self.assertEqual([p.name for p in found_vids], ["sc_01.mp4", "sc_01_v2.mp4", "sc_01_v3.mp4"])

            out_seg = proj / "work" / "sc_01_p1.mp4"
            va.render_multi_video_montage_subclip(found_vids, 0.0, 0.0, 4.5, 6.0, out_seg, allow_nvenc=False)
            self.assertTrue(out_seg.exists() and out_seg.stat().st_size > 10_000)
            self.assertAlmostEqual(probe_duration(out_seg), 4.5, delta=0.45)

    def test_flow_stage_watchdog_queue_and_handoff(self):
        from unittest import mock
        import core.flow_accounts as fa

        with tempfile.TemporaryDirectory() as td:
            wfile = Path(td) / "flow_watchdog_queue.json"
            with mock.patch.object(fa, "FLOW_WATCHDOG_FILE", wfile), \
                 mock.patch.object(fa, "_detect_untracked_pipeline_processes", return_value=[]):
                # Simula lock antigo de PID morto -> deve ser limpo automaticamente
                fa._write_watchdog_state({
                    "active_owner": {
                        "pid": 99999999,
                        "slug": "processo-morto",
                        "stage": "flow_media",
                        "started_at": 100.0,
                        "heartbeat_ts": 100.0,
                        "status": "running",
                    },
                    "queue": [],
                    "last_finished": None,
                })
                with fa.FlowStageWatchdog(slug="episodio-atual", stage="flow_media", heartbeat_interval_s=0.2) as wd:
                    st_live = fa._read_watchdog_state()
                    self.assertIsNotNone(st_live["active_owner"])
                    self.assertEqual(st_live["active_owner"]["slug"], "episodio-atual")
                    self.assertEqual(st_live["active_owner"]["pid"], wd.pid)
                st_after = fa._read_watchdog_state()
                self.assertIsNone(st_after["active_owner"])
                self.assertEqual(st_after["last_finished"]["slug"], "episodio-atual")
                self.assertEqual(st_after["last_finished"]["status"], "finished_and_notified")

    def test_unusual_activity_fast_abort_and_scenic_dog_text_allowed(self):
        import asyncio as _asyncio
        import json as _json
        from unittest import mock
        import numpy as np
        import core.flow_continuity as fc
        import core.scene_auditor as sa

        class _FakeTile:
            async def count(self):
                return 1

            async def evaluate(self, js):
                return {"hasImg": False, "hasVidReady": False, "inProgress": False, "hasRetryBtn": True, "hasErrTxt": True, "hasUnusualActivity": True}

        class _FakeLoc:
            @property
            def first(self):
                return _FakeTile()

        class _FakePage:
            def locator(self, sel):
                return _FakeLoc()

        with self.assertRaises(RuntimeError) as ctx:
            _asyncio.run(fc._retry_failed_flow_tile(_FakePage(), retries_done=0, max_retries=3))
        self.assertIn("atividade incomum", str(ctx.exception).lower())

        with tempfile.TemporaryDirectory() as td:
            img = Path(td) / "sc_14_p1.jpg"
            rng = np.random.default_rng(77)
            Image.fromarray(rng.integers(40, 220, (360, 640, 3), dtype=np.uint8)).save(img, quality=92)

            class _RespDog:
                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False

                def read(self):
                    return _json.dumps({
                        "candidates": [{"content": {"parts": [{"text": _json.dumps({
                            "matches_narration": True,
                            "matches_location": True,
                            "matches_characters": True,
                            "matches_story_props": True,
                            "has_collage_or_split": False,
                            "has_visible_text": True,
                            "reason": "A cena está ótima, apenas contém a palavra 'DOG' gravada no biscoito.",
                            "fix_prompt_hint": "",
                        })}]}}]
                    }).encode("utf-8")

            sc14 = {"scene_id": "sc_14", "act": 2, "speaker": "frida", "text": "Suba na ponte!", "location": "Ponte de Biscoito", "visual_action": "Frida e Luna na ponte", "characters": ["Frida", "Luna"]}
            with mock.patch.object(sa, "_get_google_keys", return_value=["DUMMY_TEST_KEY"]), \
                 mock.patch("urllib.request.urlopen", return_value=_RespDog()):
                res = sa.audit_scene_visual_with_vision([img], sc14, is_video_keyframes=False)
            self.assertTrue(res["ok"], res)
            self.assertFalse(res["has_visible_text"])

    def test_legacy_scanner_on_real_project(self):
        leg = Path(r"E:\videos\e-se-os-cachorros-pudessem-falar-por-um-dia")
        if leg.exists():
            rep = scan_legacy_project(leg)
            self.assertEqual(rep["words"], 2011)
            self.assertTrue(rep["bad_opening"])
            self.assertGreater(rep["written_laughs"], 10)
            self.assertIn("condensar_roteiro_3_atos_frida_luna", rep["recommended_actions"])


    def test_light_audit_releases_usable_media_but_blocks_crude(self):
        """Perfil light (padrao) libera acao divergente; so bloqueia defeito tosco."""
        import json
        import tempfile
        from unittest import mock

        from PIL import Image

        import core.scene_auditor as sa

        def _vision(payload: dict):
            resp = mock.MagicMock()
            resp.__enter__.return_value = resp
            resp.read.return_value = json.dumps({
                "candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}]
            }).encode("utf-8")
            return resp

        with tempfile.TemporaryDirectory() as td:
            img = Path(td) / "frame.jpg"
            Image.new("RGB", (640, 360), (150, 180, 200)).save(img, quality=90)
            scene = {"scene_id": "sc_08", "text": "Luna se sacode", "location": "praia", "visual_action": "shake"}

            action_mismatch = {
                "matches_narration": False, "matches_location": True, "matches_characters": True,
                "matches_story_props": True, "has_collage_or_split": False, "has_visible_text": False,
                "reason": "Luna esta parada, sem o sacodir descrito",
            }
            with mock.patch.object(sa, "_get_google_keys", return_value=["k1"]), \
                 mock.patch("urllib.request.urlopen", return_value=_vision(action_mismatch)):
                strict = sa.audit_scene_visual_with_vision([img], scene, audit_profile="strict")
                light = sa.audit_scene_visual_with_vision([img], scene, audit_profile="light")
            self.assertFalse(strict["ok"])
            self.assertTrue(light["ok"])
            self.assertIn("narration", light["relaxed_checks"])
            self.assertEqual(light["audit_profile"], "light")

            crude = {
                "matches_narration": True, "matches_location": True, "matches_characters": True,
                "matches_story_props": True, "has_collage_or_split": False, "has_visible_text": True,
                "reason": "marca d'agua gigante no centro",
            }
            with mock.patch.object(sa, "_get_google_keys", return_value=["k1"]), \
                 mock.patch("urllib.request.urlopen", return_value=_vision(crude)):
                blocked = sa.audit_scene_visual_with_vision([img], scene, audit_profile="light")
            self.assertFalse(blocked["ok"])

    def test_viral_research_structure_and_fallback(self):
        """Pesquisa de virais extrai ESTRUTURA e nunca vaza titulo/fala copiada ao roteirista."""
        from core.viral_research import (
            analyze_humor_structure,
            build_prompt_section,
            build_queries,
            parse_view_count,
        )

        self.assertEqual(parse_view_count("6.455.922 visualizações"), 6_455_922)
        self.assertEqual(parse_view_count("1.9M views"), 1_900_000)
        self.assertEqual(parse_view_count("256.859 visualizações"), 256_859)
        self.assertEqual(parse_view_count("1,2 mi visualizações"), 1_200_000)

        videos = [{
            "title": "Dogs First Time at the Beach Funny Compilation",
            "snippet": "funny fails",
            "views": 5_000_000,
        }]
        analysis = analyze_humor_structure(videos)
        names = {s["signal"] for s in analysis["signals"]}
        self.assertIn("first_time", names)
        self.assertIn("rapid_compilation", names)

        section = build_prompt_section({
            "found_viral": True, "viral_count": 1, "humor": analysis, "suggestion": None,
        })
        self.assertIn("USE A ESTRUTURA", section)
        self.assertIn("PROIBIDO copiar", section)
        self.assertNotIn("Dogs First Time", section)

        fallback = build_prompt_section({
            "found_viral": False, "viral_count": 0,
            "humor": {"signals": [], "structure": {}},
            "suggestion": "Nenhum vídeo acima de 1M encontrado. Sugestão: gancho e contraste.",
        })
        self.assertIn("Nenhum vídeo acima de 1M", fallback)
        self.assertIn("Gancho", fallback)
        queries = build_queries("Frida e Luna primeiro dia de praia muito engraçado")
        self.assertEqual(len(queries), 4)
        self.assertTrue(any("dog" in q and "beach" in q for q in queries))

    def test_comedy_timing_fields_and_multi_foley(self):
        """Regra 16: catchphrase e comedy_beat sobrevivem a normalizacao e geram ate 3 foleys."""
        from core.audio_fx import MAX_COMEDY_FOLEYS, _infer_semantic_foleys
        from core.script_engine import normalize_script_records

        raw = {
            "title": "O Primeiro Dia de Praia da Frida e Luna",
            "catchphrase": "Eu não comi, só provei... de novo!",
            "scenes": [{
                "scene_id": "sc_01",
                "act": 1,
                "speaker": "luna",
                "text": "Eita! A areia me mordeu...",
                "location": "Praia ensolarada",
                "visual_action": "Luna pula na areia com as patinhas",
                "sfx": "cartoon boing",
                "comedy_beat": "Luna pula na areia → cartoon boing → slide whistle de susto → pausa de riso",
                "avatar_mode": "luna",
            }],
        }
        norm = normalize_script_records(raw)
        self.assertEqual(norm["catchphrase"], "Eu não comi, só provei... de novo!")
        self.assertIn("cartoon boing", norm["scenes"][0]["comedy_beat"])

        hits = _infer_semantic_foleys(norm["scenes"][0])
        self.assertLessEqual(len(hits), MAX_COMEDY_FOLEYS)
        self.assertGreaterEqual(len(hits), 2)
        self.assertTrue(any("boing" in h.lower() for h, _v in hits))
        self.assertTrue(any("whistle" in h.lower() for h, _v in hits))
        self.assertTrue(all(0 < v <= 0.35 for _h, v in hits))


    def test_test_suite_catalog_integrity(self):
        """O catalogo da suíte deve estar completo: ids unicos e arquivos existentes."""
        import json

        manifest = Path(__file__).parent / "suite" / "manifest.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        entries = data.get("entries") or []
        self.assertGreaterEqual(len(entries), 25)
        ids = [e["id"] for e in entries]
        self.assertEqual(len(ids), len(set(ids)))
        root = Path(__file__).resolve().parents[1]
        missing = [e["path"] for e in entries if not (root / e["path"]).exists()]
        self.assertEqual(missing, [], f"Testes catalogados ausentes: {missing}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
