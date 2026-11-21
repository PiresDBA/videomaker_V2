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

        # 1. Trava de vozes (Kore/Sulafat/Leda sem troca)
        ok_timings = [
            {"scene_id": "sc_01", "speaker": "narrador", "voice": "gemini-3.8-flash-tts:Kore"},
            {"scene_id": "sc_02", "speaker": "frida", "voice": "gemini-3.8-flash-tts:Sulafat"},
            {"scene_id": "sc_03", "speaker": "luna", "voice": "gemini-3.8-flash-tts:Leda"},
        ]
        self.assertEqual(audit_voice_consistency(ok_timings), [])
        bad_timings = ok_timings + [
            {"scene_id": "sc_17", "speaker": "narrador", "voice": "gemini-3.8-flash-tts:Puck"},
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

    def test_legacy_scanner_on_real_project(self):
        leg = Path(r"E:\videos\e-se-os-cachorros-pudessem-falar-por-um-dia")
        if leg.exists():
            rep = scan_legacy_project(leg)
            self.assertEqual(rep["words"], 2011)
            self.assertTrue(rep["bad_opening"])
            self.assertGreater(rep["written_laughs"], 10)
            self.assertIn("condensar_roteiro_3_atos_frida_luna", rep["recommended_actions"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
