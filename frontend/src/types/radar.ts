export interface ReferenceItem {
  fuente: string;
  titulo: string;
  autor: string;
  fecha: string;
  metricas?: Record<string, any>;
  url: string;
}

export interface DecisionQuestionItem {
  id: string;
  pregunta: string;
  respuesta: string;
  score: number;
  razonamiento: string;
}

export interface DecisionAuditData {
  veredicto: "APROBADO" | "EN_OBSERVACION" | "DESCARTADO";
  motivo_veredicto: string;
  palabras_clave_detectadas: string[];
  desglose_formula: Record<string, number>;
  preguntas: DecisionQuestionItem[];
}

export interface CriticVerdictData {
  narrative_id: string;
  veracidad_p: number;
  impacto_real: number;
  humo_p: number;
  veredicto: "valido" | "dudoso" | "descartado";
  razones: string[];
  fuentes_verificadas: string[];
  tiene_fuente_primaria: boolean;
  penalidad_clickbait: number;
  evaluado_at?: string;
}

export interface Adaptacion30XObject {
  formato_sugerido?: string;
  titular_gancho?: string;
  [key: string]: any;
}

export type Adaptacion30X = string | Adaptacion30XObject;

export interface DeepScrapedContent {
  url: string;
  metodo: string;
  titulo: string;
  tokens_estimados: number;
  costo_estimado: string;
  resumen_markdown: string;
  autor?: string;
}

export interface TrendItem {
  posicion: number;
  tema: string;
  fase: string;
  confianza_jev: number;
  crecimiento: string;
  score: number;
  fuentes: string[];
  gancho: string;
  formato: string;
  encaje_audiencia: number;
  por_que: string;
  por_que_audiencia?: string;
  adaptacion_30x: Adaptacion30X;
  evidencia: string[];
  referencias_detalladas?: ReferenceItem[];
  contenido_profundo?: DeepScrapedContent;
  proceso_decision?: DecisionAuditData;
  sparkline?: string;
  novedad?: number;
  veredicto_critico?: CriticVerdictData;
}

export interface DiscardedItem {
  tema: string;
  fuentes: string[];
  score: number;
  motivo: string;
  veredicto: string;
}

export interface ObservationItem {
  tema: string;
  fuentes: string[];
  score: number;
  crecimiento: string;
  motivo: string;
  veredicto: string;
  evidencia?: string[];
  referencias_detalladas?: ReferenceItem[];
}

export interface ReportData {
  semana: string;
  generado: string;
  total_clusters_evaluados: number;
  embudo_metricas?: {
    total_evaluados: number;
    aprobados_top: number;
    en_observacion: number;
    descartados: number;
  };
  top_temas: TrendItem[];
  temas_descartados?: DiscardedItem[];
  temas_en_observacion?: ObservationItem[];
}

export interface SearchFocus {
  id: string;
  nombre: string;
  categoria: string;
  descripcion: string;
  keywords: string[];
  activo: boolean;
  creado_en?: string;
}

export interface RSSAppFeedItem {
  id: string;
  nombre: string;
  url: string;
  plataforma: "Twitter/X" | "TikTok" | "LinkedIn" | "YouTube" | "Web" | "General";
  enfoque_id: string;
  activo: boolean;
  ultimo_sync?: string;
  total_items_capturados: number;
  creado_en?: string;
}

export interface HookAnalysis {
  tipo_gancho: string;
  texto_primeros_15s: string;
  analisis_gancho: string;
  plantilla_reutilizable: string;
}

export interface KnowledgeProfile {
  source_id: string;
  modo_extraccion?: "ganchos" | "keywords" | "completo" | string;
  hook?: HookAnalysis;
  estructura_narrativa?: Array<{ etapa: string; segundos: string; proposito: string }>;
  tono_y_voz?: string;
  conceptos_clave?: string[];
  plantillas_30x?: string[];
  resumen_ejecutivo: string;
  palabras_clave?: string[];
  palabras_clave_secundarias?: string[];
  entidades_detectadas?: string[];
  enfoques_radar_sugeridos?: string[];
  texto_extraido?: string;
}

export interface KnowledgeSource {
  id: string;
  tipo: "image" | "image_pool" | "youtube" | "video" | "file" | "url" | "texto" | string;
  modo_extraccion?: "ganchos" | "keywords" | "completo" | string;
  url_o_path: string;
  imagen_preview?: string | null;
  imagenes_pool?: string[];
  total_imagenes?: number;
  titulo: string;
  autor: string;
  duracion_segundos: number;
  solicitud_usuario: string;
  transcripcion_resumen: string;
  creado_en: string;
  perfil?: KnowledgeProfile;
}

export interface PlaygroundResult {
  tema: string;
  fuentes: string[];
  vistas_por_hora: number;
  preguntas_jev: Array<{
    id: string;
    pregunta: string;
    respuesta?: string;
    score?: number;
    razonamiento?: string;
    opciones?: string[];
    proposito: string;
  }>;
  decision: {
    fase: string;
    gancho: string;
    formato: string;
    novedad: number;
    encaje_audiencia: number;
    confianza: number;
  };
  score_final: number;
  crecimiento_label: string;
  score_breakdown: Record<string, any>;
  latencia_ms: number;
  motor_utilizado: string;
}

export interface DraftItem {
  id: number;
  tema_id?: number | null;
  narrative_id?: string | null;
  titulo: string;
  formato: string;
  gancho: string;
  autor: string;
  estado: "borrador" | "en_revision" | "aprobado" | "publicado";
  version: number;
  body?: string;
  content?: string;
  file_path?: string;
  created_at: string;
  updated_at: string;
}

export interface BibliographySource {
  id: string;
  name: string;
  categoria: string;
  tipo: string;
  cadencia: string;
  descripcion: string;
  canales_destacados: string[];
  url_oficial: string;
  estado: string;
  compliance: string;
  total_items?: number;
}

export interface SuggestedSource {
  id: string;
  name: string;
  categoria: string;
  impacto: string;
  beneficio: string;
  dificultad: string;
  url: string;
}

export interface BibliographyResponse {
  resumen: {
    total_fuentes_activas: number;
    total_items_indexados: number;
    categorias_cubiertas: string[];
    fuentes_sugeridas_expansion: number;
  };
  active_sources: BibliographySource[];
  suggested_sources: SuggestedSource[];
}

export const getApiBase = () => {
  if (typeof window !== "undefined") {
    if (window.location.port === "8080" || window.location.port === "") {
      return "";
    }
    return `${window.location.protocol}//${window.location.hostname}:8080`;
  }
  return "http://localhost:8080";
};
