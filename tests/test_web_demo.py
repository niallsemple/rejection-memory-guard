import os
import web_demo


def test_web_demo_examples(tmp_path):
    os.environ["RMG_OFFLINE"] = "1"
    state = web_demo.DemoState(str(tmp_path))
    try:
        assert len(state.rejections()) == 2
        for ex in web_demo.EXAMPLES:
            assert state.check(ex["candidate"], ex["conditions"])["decision"] == ex["expect"], ex
        assert state.check("Write unit tests for the date parser")["decision"] == "ALLOW"
        state.add_rejection("Use a global mutex for the order book", "contention")
        assert len(state.rejections()) == 3
        state.reset()
        assert len(state.rejections()) == 2
        assert "REJECTED APPROACHES" in state.injection()
        assert "__EXAMPLES__" not in web_demo.render_page()
    finally:
        state.close()
