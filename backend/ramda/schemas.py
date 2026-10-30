import re
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Localized(BaseModel):
    id: str = ""
    en: str = ""


class TextModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def safe_links(self):
        def check(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if (key.endswith("url") or key in {"href", "src"}) and isinstance(item, str) and item:
                        if not (item.startswith(("/", "#", "https://", "http://", "mailto:"))):
                            raise ValueError(f"Unsafe URL in {key}")
                        if item.startswith("//") or any(c in item for c in "\r\n\\"):
                            raise ValueError("Invalid URL")
                    check(item)
            elif isinstance(value, list):
                for item in value:
                    check(item)
        check(self.model_dump())
        return self


class Cta(TextModel):
    label: Localized = Field(default_factory=Localized)
    url: str = ""


class ImageRef(TextModel):
    src: str = ""
    alt: Localized = Field(default_factory=Localized)
    width: int = 0
    height: int = 0
    variants: list[dict] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_alt(self):
        if self.src and (not self.alt.id or self.width <= 0 or self.height <= 0):
            raise ValueError("Images need Indonesian alt text and positive dimensions")
        return self


class Settings(TextModel):
    brand_name: str = ""
    tagline: Localized = Field(default_factory=Localized)
    logo_light: ImageRef = Field(default_factory=ImageRef)
    logo_dark: ImageRef = Field(default_factory=ImageRef)
    favicon_url: str = ""
    contact_email: str = ""
    whatsapp_number: str = ""
    whatsapp_message: Localized = Field(default_factory=Localized)
    social_links: dict[str, str] = Field(default_factory=dict)
    availability_on: bool = False
    availability_text: Localized = Field(default_factory=Localized)
    footer_text: Localized = Field(default_factory=Localized)
    seo_title_template: str = "%s | RAMDA"
    seo_description: Localized = Field(default_factory=Localized)
    og_image: ImageRef = Field(default_factory=ImageRef)
    analytics_script_url: str = ""
    analytics_site_id: str = ""
    navigation: list[Cta] = Field(default_factory=list)
    primary_cta: Cta = Field(default_factory=Cta)
    secondary_cta: Cta = Field(default_factory=Cta)
    contact_title: Localized = Field(default_factory=Localized)
    contact_description: Localized = Field(default_factory=Localized)
    contact_success: Localized = Field(default_factory=Localized)
    project_types: list[Localized] = Field(default_factory=list)
    budget_ranges: list[Localized] = Field(default_factory=list)
    notifications_enabled: bool = False

    @field_validator("social_links")
    @classmethod
    def social_urls(cls, value):
        if any(not v.startswith("https://") for v in value.values() if v):
            raise ValueError("Social links must use HTTPS")
        return value

    @field_validator("whatsapp_number")
    @classmethod
    def phone(cls, value):
        if value and not re.fullmatch(r"[1-9][0-9]{7,14}", value):
            raise ValueError("Use international digits, e.g. 628..., without +")
        return value


class Section(TextModel):
    key: Literal["navbar", "hero", "stats", "projects", "ai", "services", "process", "about", "articles", "pricing", "testimonials", "faq", "cta", "footer"]
    enabled: bool = True
    eyebrow: Localized = Field(default_factory=Localized)
    title: Localized = Field(default_factory=Localized)
    subtitle: Localized = Field(default_factory=Localized)
    cta: Cta = Field(default_factory=Cta)


class Hero(TextModel):
    eyebrow: Localized = Field(default_factory=Localized)
    headline: Localized = Field(default_factory=Localized)
    highlighted_words: Localized = Field(default_factory=Localized)
    subheadline: Localized = Field(default_factory=Localized)
    primary_cta: Cta = Field(default_factory=Cta)
    secondary_cta: Cta = Field(default_factory=Cta)
    background_image: ImageRef = Field(default_factory=ImageRef)
    script_tagline: Localized = Field(default_factory=Localized)
    intro_video_url: str = ""


class Stat(TextModel):
    value: str
    label: Localized
    sublabel: Localized = Field(default_factory=Localized)
    icon: str = "sparkles"
    visible: bool = False


class Project(TextModel):
    title: Localized
    summary: Localized
    status: Literal["live", "in_development", "in_planning", "mvp", "academic", "archived"]
    stack_tags: list[str] = Field(default_factory=list)
    cover: ImageRef = Field(default_factory=ImageRef)
    gallery: list[ImageRef] = Field(default_factory=list)
    metrics: list[dict[str, str]] = Field(default_factory=list)
    live_url: str = ""
    repo_url: str = ""
    since: str = ""
    featured: bool = False
    problem: Localized = Field(default_factory=Localized)
    solution: Localized = Field(default_factory=Localized)
    result: Localized = Field(default_factory=Localized)


class Service(TextModel):
    title: Localized
    description: Localized
    icon: str = "code"
    bullets: list[Localized] = Field(default_factory=list)
    visible: bool = True


class Package(TextModel):
    name: Localized
    price_text: Localized
    description: Localized
    features: list[Localized] = Field(default_factory=list)
    highlighted: bool = False
    cta: Cta = Field(default_factory=Cta)
    visible: bool = True


class ProcessStep(TextModel):
    number: str
    title: Localized
    description: Localized


class TechItem(TextModel):
    name: str
    icon: str = "code"
    image: ImageRef = Field(default_factory=ImageRef)
    category: str = ""
    show_on_home: bool = True


class About(TextModel):
    name: str
    role: Localized
    bio: Localized
    photo: ImageRef = Field(default_factory=ImageRef)
    highlight_cards: list[dict] = Field(default_factory=list)


class Testimonial(TextModel):
    author_name: str
    role: Localized = Field(default_factory=Localized)
    company: str = ""
    quote: Localized
    avatar: ImageRef = Field(default_factory=ImageRef)
    consent_given: bool = False


class Article(TextModel):
    title: Localized
    excerpt: Localized
    cover: ImageRef = Field(default_factory=ImageRef)
    category: Localized = Field(default_factory=Localized)
    tags: list[str] = Field(default_factory=list)
    body: Localized
    status: Literal["draft", "published"] = "draft"
    published_at: str = ""
    seo_title: Localized = Field(default_factory=Localized)
    seo_description: Localized = Field(default_factory=Localized)
    og_image: ImageRef = Field(default_factory=ImageRef)


    @field_validator("published_at")
    @classmethod
    def timestamp(cls, value):
        if value:
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError("published_at needs a timezone offset")
        return value


class Faq(TextModel):
    question: Localized
    answer: Localized


class AiConfig(TextModel):
    enabled: bool = False
    model: str = ""
    system_prompt: str = ""
    welcome_message: Localized = Field(default_factory=Localized)
    suggestions: list[Localized] = Field(default_factory=list)
    disclaimer: Localized = Field(default_factory=Localized)
    offline_message: Localized = Field(default_factory=Localized)
    limit_message: Localized = Field(default_factory=Localized)
    input_placeholder: Localized = Field(default_factory=Localized)
    max_input_chars: int = Field(default=500, ge=1, le=500)
    max_output_tokens: int = Field(default=256, ge=16, le=1024)
    max_turns: int = Field(default=6, ge=1, le=6)
    requests_per_hour: int = Field(default=10, ge=1, le=60)
    daily_budget_usd: float = Field(default=1, ge=0, le=100)
    kill_switch: bool = False


class KnowledgeDoc(TextModel):
    title: str
    body: str
    enabled: bool = True


SCHEMAS = {"settings": Settings, "section": Section, "hero": Hero, "stat": Stat, "project": Project, "service": Service, "package": Package, "process": ProcessStep, "tech": TechItem, "about": About, "testimonial": Testimonial, "article": Article, "faq": Faq, "ai_config": AiConfig, "knowledge": KnowledgeDoc}
SINGLETONS = {"settings", "hero", "about", "ai_config"}


class ContactInput(TextModel):
    name: str = Field(min_length=2, max_length=100)
    contact: str = Field(min_length=5, max_length=254)
    project_type: str = Field(min_length=1, max_length=100)
    budget_range: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=10, max_length=4000)
    website: str = ""
    turnstile_token: str = Field(default="", max_length=4096)


class ChatMessage(TextModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatInput(TextModel):
    message: str = Field(min_length=1, max_length=500)
    history: list[ChatMessage] = Field(default_factory=list, max_length=10)
    turnstile_token: str = Field(default="", max_length=4096)
    session_token: str = Field(default="", max_length=2000)
