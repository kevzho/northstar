"use client";

/**
 * Lightweight dictionary i18n for the marketing surfaces (footer, FAQ,
 * contact, and the landing hero). Deliberately NOT a full-app framework:
 * it covers exactly the strings these pages render, so nothing shows up
 * half-translated. The choice persists in localStorage and is read
 * through useSyncExternalStore so server and client agree on first paint.
 *
 * Adding a language = add its column to `dictionary`. Adding a string =
 * add its key with every language filled in (a missing key falls back to
 * English so a partial translation degrades to readable, never blank).
 */

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useSyncExternalStore,
} from "react";

export const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "es", label: "Español" },
  { code: "zh", label: "中文" },
  { code: "fr", label: "Français" },
] as const;

export type LanguageCode = (typeof LANGUAGES)[number]["code"];

type Dict = Record<string, string>;

const dictionary: Record<LanguageCode, Dict> = {
  en: {
    "footer.contact": "Contact",
    "footer.faq": "FAQ",
    "footer.language": "Language",
    "footer.rights": "A student-built opportunity map.",

    "contact.eyebrow": "Get in touch",
    "contact.title": "Contact",
    "contact.intro":
      "Questions, a program to add, feedback, or a partnership — reach the maker directly.",
    "contact.email": "Email",
    "contact.response": "Replies usually land within a couple of days.",
    "contact.suggest": "Suggest an opportunity",
    "contact.suggestBody":
      "Know a program, scholarship, or competition students should see? Send the link and a line about who it fits.",
    "contact.back": "Back home",

    "faq.eyebrow": "Questions & answers",
    "faq.title": "FAQ",
    "faq.intro": "How Northstar works, and what it will and won't do.",
    "faq.back": "Back home",
    "faq.q1": "What is Northstar?",
    "faq.a1":
      "A career-navigation tool for students. A short behavioral assessment builds a transparent profile of how you think and work, then turns it into future paths, real opportunities with reasons attached, and a plan you can act on.",
    "faq.q2": "Is this just an AI chatbot?",
    "faq.a2":
      "No. The recommendations come from an interpretable scoring engine — every match shows the exact reasons behind its score. Nothing is a black box, and no AI decides who you are.",
    "faq.q3": "How much does it cost?",
    "faq.a3": "Nothing. Northstar is free for students.",
    "faq.q4": "Where do the opportunities come from?",
    "faq.a4":
      "Most of the catalog is hand-picked and checked by a person. The rest is gathered from public sources through official APIs and screened by an automated verifier before it enters the catalog. Either way a real program is behind every entry — nothing unverified is shown as one.",
    "faq.q5": "Is my data private?",
    "faq.a5":
      "Your profile is private by default. Public evidence pages and friend comparisons are opt-in, and negative outcomes are never made public.",
    "faq.q6": "Who built this?",
    "faq.a6":
      "Northstar is a student project — built, and its algorithms designed and validated, by one person.",
  },
  es: {
    "footer.contact": "Contacto",
    "footer.faq": "Preguntas",
    "footer.language": "Idioma",
    "footer.rights": "Un mapa de oportunidades hecho por un estudiante.",

    "contact.eyebrow": "Ponte en contacto",
    "contact.title": "Contacto",
    "contact.intro":
      "Preguntas, un programa para añadir, comentarios o una colaboración — escribe directamente al creador.",
    "contact.email": "Correo",
    "contact.response": "Las respuestas suelen llegar en un par de días.",
    "contact.suggest": "Sugerir una oportunidad",
    "contact.suggestBody":
      "¿Conoces un programa, beca o concurso que los estudiantes deberían ver? Envía el enlace y una línea sobre a quién le sirve.",
    "contact.back": "Volver al inicio",

    "faq.eyebrow": "Preguntas y respuestas",
    "faq.title": "Preguntas frecuentes",
    "faq.intro": "Cómo funciona Northstar, y lo que hará y no hará.",
    "faq.back": "Volver al inicio",
    "faq.q1": "¿Qué es Northstar?",
    "faq.a1":
      "Una herramienta de orientación profesional para estudiantes. Una breve evaluación de comportamiento crea un perfil transparente de cómo piensas y trabajas, y lo convierte en caminos futuros, oportunidades reales con razones, y un plan que puedes seguir.",
    "faq.q2": "¿Es solo un chatbot de IA?",
    "faq.a2":
      "No. Las recomendaciones vienen de un motor de puntuación interpretable — cada coincidencia muestra las razones exactas de su puntuación. Nada es una caja negra, y ninguna IA decide quién eres.",
    "faq.q3": "¿Cuánto cuesta?",
    "faq.a3": "Nada. Northstar es gratis para estudiantes.",
    "faq.q4": "¿De dónde vienen las oportunidades?",
    "faq.a4":
      "La mayor parte del catálogo está seleccionada y comprobada a mano. El resto se recopila de fuentes públicas mediante APIs oficiales y pasa por un verificador automático antes de entrar. En ambos casos hay un programa real detrás de cada entrada; nada sin verificar se muestra como tal.",
    "faq.q5": "¿Mis datos son privados?",
    "faq.a5":
      "Tu perfil es privado por defecto. Las páginas públicas y las comparaciones con amigos son opcionales, y los resultados negativos nunca se hacen públicos.",
    "faq.q6": "¿Quién lo creó?",
    "faq.a6":
      "Northstar es un proyecto estudiantil — construido, y con sus algoritmos diseñados y validados, por una sola persona.",
  },
  zh: {
    "footer.contact": "联系",
    "footer.faq": "常见问题",
    "footer.language": "语言",
    "footer.rights": "一个由学生打造的机会地图。",

    "contact.eyebrow": "联系我们",
    "contact.title": "联系",
    "contact.intro":
      "问题、想推荐的项目、反馈或合作 — 都可以直接联系作者。",
    "contact.email": "电子邮件",
    "contact.response": "通常会在几天内回复。",
    "contact.suggest": "推荐一个机会",
    "contact.suggestBody":
      "知道学生应该看到的项目、奖学金或竞赛吗？发送链接并简述它适合谁。",
    "contact.back": "返回主页",

    "faq.eyebrow": "问答",
    "faq.title": "常见问题",
    "faq.intro": "Northstar 如何运作，以及它会做和不会做什么。",
    "faq.back": "返回主页",
    "faq.q1": "Northstar 是什么？",
    "faq.a1":
      "一个为学生提供的职业导航工具。简短的行为评估会建立一个透明的档案，反映你如何思考和工作，然后转化为未来路径、附带理由的真实机会，以及一个可执行的计划。",
    "faq.q2": "这只是一个 AI 聊天机器人吗？",
    "faq.a2":
      "不是。推荐来自一个可解释的评分引擎 — 每个匹配都会显示其分数的确切原因。没有黑箱，也没有 AI 来决定你是谁。",
    "faq.q3": "费用是多少？",
    "faq.a3": "免费。Northstar 对学生免费。",
    "faq.q4": "这些机会从哪里来？",
    "faq.a4":
      "目录中的大部分条目由人工挑选并核实，其余部分通过官方 API 从公开来源收集，并经自动验证器筛查后才进入目录。无论哪种方式，每条记录背后都是真实存在的项目；未经核实的内容不会被展示为真实项目。",
    "faq.q5": "我的数据是私密的吗？",
    "faq.a5":
      "你的档案默认是私密的。公开的成果页面和好友比较都是自愿选择的，负面结果永远不会公开。",
    "faq.q6": "这是谁做的？",
    "faq.a6":
      "Northstar 是一个学生项目 — 由一个人构建，其算法也由这个人设计和验证。",
  },
  fr: {
    "footer.contact": "Contact",
    "footer.faq": "FAQ",
    "footer.language": "Langue",
    "footer.rights": "Une carte des opportunités créée par un étudiant.",

    "contact.eyebrow": "Nous contacter",
    "contact.title": "Contact",
    "contact.intro":
      "Questions, un programme à ajouter, des retours ou un partenariat — écrivez directement au créateur.",
    "contact.email": "E-mail",
    "contact.response": "Les réponses arrivent généralement en quelques jours.",
    "contact.suggest": "Proposer une opportunité",
    "contact.suggestBody":
      "Vous connaissez un programme, une bourse ou un concours que les étudiants devraient voir ? Envoyez le lien et une ligne sur qui cela concerne.",
    "contact.back": "Retour à l'accueil",

    "faq.eyebrow": "Questions & réponses",
    "faq.title": "FAQ",
    "faq.intro": "Comment fonctionne Northstar, et ce qu'il fera ou non.",
    "faq.back": "Retour à l'accueil",
    "faq.q1": "Qu'est-ce que Northstar ?",
    "faq.a1":
      "Un outil d'orientation pour les étudiants. Une courte évaluation comportementale crée un profil transparent de votre façon de penser et de travailler, puis le transforme en parcours futurs, en opportunités réelles justifiées, et en un plan à suivre.",
    "faq.q2": "Est-ce juste un chatbot IA ?",
    "faq.a2":
      "Non. Les recommandations viennent d'un moteur de notation interprétable — chaque correspondance montre les raisons exactes de son score. Rien n'est une boîte noire, et aucune IA ne décide qui vous êtes.",
    "faq.q3": "Combien ça coûte ?",
    "faq.a3": "Rien. Northstar est gratuit pour les étudiants.",
    "faq.q4": "D'où viennent les opportunités ?",
    "faq.a4":
      "La majeure partie du catalogue est sélectionnée et vérifiée à la main. Le reste est recueilli de sources publiques via des API officielles et passe par un vérificateur automatique avant d'entrer au catalogue. Dans les deux cas, un programme réel se trouve derrière chaque entrée ; rien de non vérifié n'est présenté comme tel.",
    "faq.q5": "Mes données sont-elles privées ?",
    "faq.a5":
      "Votre profil est privé par défaut. Les pages publiques et les comparaisons entre amis sont facultatives, et les résultats négatifs ne sont jamais rendus publics.",
    "faq.q6": "Qui a créé ceci ?",
    "faq.a6":
      "Northstar est un projet étudiant — construit, et ses algorithmes conçus et validés, par une seule personne.",
  },
};

const STORAGE_KEY = "northstar.language";
const listeners = new Set<() => void>();

function getSnapshot(): LanguageCode {
  const stored = window.localStorage.getItem(STORAGE_KEY) as LanguageCode | null;
  return stored && stored in dictionary ? stored : "en";
}

function subscribe(callback: () => void) {
  listeners.add(callback);
  return () => listeners.delete(callback);
}

const LanguageContext = createContext<{
  lang: LanguageCode;
  setLang: (code: LanguageCode) => void;
  t: (key: string) => string;
}>({ lang: "en", setLang: () => {}, t: (key) => key });

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  // Server snapshot is always English so first paint matches; the client
  // snapshot reads localStorage and re-renders if the choice differs.
  const lang = useSyncExternalStore(
    subscribe,
    getSnapshot,
    () => "en" as LanguageCode,
  );

  const setLang = useCallback((code: LanguageCode) => {
    window.localStorage.setItem(STORAGE_KEY, code);
    listeners.forEach((l) => l());
  }, []);

  const t = useCallback(
    (key: string) => dictionary[lang][key] ?? dictionary.en[key] ?? key,
    [lang],
  );

  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t]);
  return (
    <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}
