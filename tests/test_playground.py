"""Pruebas unitarias para el Playground y Telemetría de Jev."""

from pipeline.playground import evaluate_playground_item, PlaygroundTelemetry


def test_evaluate_playground_item():
    tema = "Claude 3.5 Sonnet supera a modelos propietarios en benchmarks de razonamiento"
    telemetry = evaluate_playground_item(
        tema=tema,
        fuentes=["HackerNews", "YouTube", "GitHub"],
        vistas_por_hora=420.0,
        titulos_muestra=[tema],
    )

    assert isinstance(telemetry, PlaygroundTelemetry)
    assert telemetry.tema == tema
    assert len(telemetry.preguntas_jev) == 5
    assert telemetry.decision.fase in ["naciendo", "en_crecimiento", "saturado"]
    assert telemetry.decision.gancho in ["dato_contraintuitivo", "opinion", "tutorial", "contraste", "historia"]
    assert telemetry.decision.formato in ["video_corto", "carousel", "hilo", "long_form", "articulo"]
    assert 0.0 <= telemetry.decision.confianza <= 1.0
    assert 0.0 <= telemetry.score_final <= 2.0
    assert telemetry.latencia_ms > 0
    assert "score_breakdown" in telemetry.model_dump()
