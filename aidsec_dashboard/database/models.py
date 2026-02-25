"""SQLAlchemy Models for AidSec Lead Dashboard"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import enum

Base = declarative_base()


class LeadStatus(str, enum.Enum):
    OFFEN = "offen"
    PENDING = "pending"
    RESPONSE_RECEIVED = "response_received"
    OFFER_SENT = "offer_sent"
    NEGOTIATION = "negotiation"
    GEWONNEN = "gewonnen"
    VERLOREN = "verloren"


class LeadKategorie(str, enum.Enum):
    ANWALT = "anwalt"
    PRAXIS = "praxis"
    WORDPRESS = "wordpress"


class EmailStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    FAILED = "failed"


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        Index("ix_leads_status", "status"),
        Index("ix_leads_kategorie", "kategorie"),
        Index("ix_leads_email", "email"),
        Index("ix_leads_website", "website"),
        Index("ix_leads_created_at", "created_at"),
        Index("ix_leads_ranking_grade", "ranking_grade"),
        Index("ix_leads_research_status", "research_status"),
        Index("ix_leads_stadt", "stadt"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    firma = Column(String(255), nullable=False)
    website = Column(String(500), nullable=True)
    email = Column(String(255), nullable=True)
    telefon = Column(String(50), nullable=True)
    stadt = Column(String(100), nullable=True)
    kategorie = Column(SQLEnum(LeadKategorie), default=LeadKategorie.ANWALT)
    status = Column(SQLEnum(LeadStatus), default=LeadStatus.OFFEN)
    
    # Financials & Stats
    deal_size = Column(Integer, nullable=True, default=0)
    response_time_hours = Column(Integer, nullable=True, default=0)

    # Ranking
    ranking_score = Column(Integer, nullable=True)
    ranking_grade = Column(String(1), nullable=True)
    ranking_details = Column(JSON, nullable=True)
    ranking_checked_at = Column(DateTime, nullable=True)

    # WordPress specific (kept as String for backward compatibility with existing data)
    wordpress_detected = Column(String(10), nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    # Metadata
    quelle = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Research fields (web scraping)
    research_status = Column(String(20), nullable=True)  # pending, in_progress, completed, failed
    research_last = Column(DateTime, nullable=True)
    research_data = Column(JSON, nullable=True)

    # Social profiles
    linkedin = Column(String(500), nullable=True)
    xing = Column(String(500), nullable=True)

    # Relationships
    status_history = relationship("StatusHistory", back_populates="lead", cascade="all, delete-orphan")
    email_history = relationship("EmailHistory", back_populates="lead", cascade="all, delete-orphan")
    follow_ups = relationship("FollowUp", back_populates="lead", cascade="all, delete-orphan")
    enrichment = relationship("LeadEnrichment", back_populates="lead", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Lead(id={self.id}, firma='{self.firma}', status='{self.status}')>"


class LeadEnrichment(Base):
    __tablename__ = "lead_enrichments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, unique=True)
    
    # Scraped Data
    about_us = Column(Text, nullable=True)
    mission_statement = Column(Text, nullable=True)
    services_offered = Column(JSON, nullable=True)
    
    # Advanced Security Checks
    ssl_valid = Column(Boolean, nullable=True)
    ssl_issuer = Column(String(255), nullable=True)
    dns_sec = Column(Boolean, nullable=True)
    cms_detected = Column(String(100), nullable=True) # e.g. WordPress, Joomla, etc.
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    lead = relationship("Lead", back_populates="enrichment")


class StatusHistory(Base):
    __tablename__ = "status_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    von_status = Column(SQLEnum(LeadStatus), nullable=True)
    zu_status = Column(SQLEnum(LeadStatus), nullable=False)
    datum = Column(DateTime, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="status_history")


class EmailHistory(Base):
    __tablename__ = "email_history"
    __table_args__ = (
        Index("ix_emailhistory_status", "status"),
        Index("ix_emailhistory_gesendet_at", "gesendet_at"),
        Index("ix_emailhistory_lead_id", "lead_id"),
        Index("ix_emailhistory_ab_test", "ab_test_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    betreff = Column(String(500), nullable=False)
    inhalt = Column(Text, nullable=False)
    status = Column(SQLEnum(EmailStatus), default=EmailStatus.DRAFT)
    gesendet_at = Column(DateTime, nullable=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    outlook_message_id = Column(String(100), nullable=True)  # For Outlook sync

    # A/B Testing
    ab_test_id = Column(Integer, nullable=True)
    ab_variant = Column(String(1), nullable=True)  # 'A' or 'B'

    # Tracking
    opened_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)
    replied_at = Column(DateTime, nullable=True)

    lead = relationship("Lead", back_populates="email_history")
    campaign = relationship("Campaign", back_populates="email_history")


class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    betreff = Column(String(500), nullable=False)
    inhalt = Column(Text, nullable=False)
    kategorie = Column(SQLEnum(LeadKategorie), nullable=True)
    # A/B Testing
    is_ab_test = Column(Boolean, default=False)
    # Versionierung
    version = Column(Integer, default=1)
    parent_template_id = Column(Integer, ForeignKey("email_templates.id"), nullable=True)
    # Definierbare Variablen
    variables = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Self-referential relationship for versioning
    parent = relationship(
        "EmailTemplate",
        remote_side=[id],
        foreign_keys=[parent_template_id],
        back_populates="children",
    )
    children = relationship(
        "EmailTemplate",
        foreign_keys=[parent_template_id],
        back_populates="parent",
    )

    def __repr__(self):
        return f"<EmailTemplate(id={self.id}, name='{self.name}', v{self.version})>"


class SequenceStatus(str, enum.Enum):
    ENTWURF = "entwurf"
    AKTIV = "aktiv"
    PAUSIERT = "pausiert"
    ABGESCHLOSSEN = "abgeschlossen"


class EmailSequence(Base):
    """Email outreach sequences with multiple steps"""
    __tablename__ = "email_sequences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    beschreibung = Column(Text, nullable=True)
    # JSON Array: [{"day_offset": 0, "template_id": 1, "subject_override": ""}, {"day_offset": 3, "template_id": 2}]
    steps = Column(JSON, nullable=False, default=list)
    status = Column(SQLEnum(SequenceStatus), default=SequenceStatus.ENTWURF)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lead_assignments = relationship("LeadSequenceAssignment", back_populates="sequence", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<EmailSequence(id={self.id}, name='{self.name}', status='{self.status}')>"


class LeadSequenceAssignment(Base):
    """Assignment of a lead to an email sequence"""
    __tablename__ = "lead_sequence_assignments"
    __table_args__ = (
        Index("ix_lsa_sequence_id", "sequence_id"),
        Index("ix_lsa_lead_id", "lead_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    sequence_id = Column(Integer, ForeignKey("email_sequences.id"), nullable=False)
    current_step = Column(Integer, default=0)
    next_send_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="aktiv")  # aktiv, pausiert, abgeschlossen, abgemeldet
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    lead = relationship("Lead")
    sequence = relationship("EmailSequence", back_populates="lead_assignments")

    def __repr__(self):
        return f"<LeadSequenceAssignment(lead={self.lead_id}, seq={self.sequence_id}, step={self.current_step})>"


class ABTest(Base):
    """A/B Test configuration for email subject lines"""
    __tablename__ = "ab_tests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    template_id = Column(Integer, ForeignKey("email_templates.id"), nullable=True)
    # Subject line variants
    subject_a = Column(String(500), nullable=False)
    subject_b = Column(String(500), nullable=False)
    # Distribution (default 50/50)
    distribution_a = Column(Integer, default=50)
    distribution_b = Column(Integer, default=50)
    # Status
    status = Column(String(20), default="draft")  # draft, running, completed
    winner = Column(String(1), nullable=True)  # 'A' or 'B'
    # Criteria for auto-winner
    auto_winner_after = Column(Integer, default=20)  # Number of sends before auto-select
    # Tracking
    sent_a = Column(Integer, default=0)
    sent_b = Column(Integer, default=0)
    opens_a = Column(Integer, default=0)
    opens_b = Column(Integer, default=0)
    clicks_a = Column(Integer, default=0)
    clicks_b = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<ABTest(id={self.id}, name='{self.name}', status='{self.status}')>"


class CampaignStatus(str, enum.Enum):
    ENTWURF = "entwurf"
    AKTIV = "aktiv"
    PAUSIERT = "pausiert"
    ABGESCHLOSSEN = "abgeschlossen"


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    beschreibung = Column(Text, nullable=True)
    kategorie_filter = Column(SQLEnum(LeadKategorie), nullable=True)
    sequenz = Column(JSON, nullable=True)
    start_datum = Column(DateTime, nullable=True)
    end_datum = Column(DateTime, nullable=True)
    status = Column(SQLEnum(CampaignStatus), default=CampaignStatus.ENTWURF)
    created_at = Column(DateTime, default=datetime.utcnow)

    campaign_leads = relationship("CampaignLead", back_populates="campaign", cascade="all, delete-orphan")
    email_history = relationship("EmailHistory", back_populates="campaign")

    def __repr__(self):
        return f"<Campaign(id={self.id}, name='{self.name}', status='{self.status}')>"


class CampaignLead(Base):
    __tablename__ = "campaign_leads"
    __table_args__ = (
        Index("ix_campaignlead_campaign_id", "campaign_id"),
        Index("ix_campaignlead_lead_id", "lead_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    current_step = Column(Integer, default=0)
    next_send_at = Column(DateTime, nullable=True)
    cl_status = Column(String(20), default="aktiv")
    created_at = Column(DateTime, default=datetime.utcnow)

    campaign = relationship("Campaign", back_populates="campaign_leads")
    lead = relationship("Lead")

    def __repr__(self):
        return f"<CampaignLead(campaign_id={self.campaign_id}, lead_id={self.lead_id}, step={self.current_step})>"


class FollowUp(Base):
    __tablename__ = "follow_ups"
    __table_args__ = (
        Index("ix_followups_datum", "datum"),
        Index("ix_followups_erledigt", "erledigt"),
        Index("ix_followups_lead_id", "lead_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    datum = Column(DateTime, nullable=False)
    notiz = Column(Text, default="")
    erledigt = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="follow_ups")

    def __repr__(self):
        return f"<FollowUp(lead_id={self.lead_id}, datum='{self.datum}', erledigt={self.erledigt})>"


class MarketingIdeaTracker(Base):
    __tablename__ = "marketing_idea_tracker"

    id = Column(Integer, primary_key=True, autoincrement=True)
    idea_number = Column(Integer, unique=True, nullable=False)
    status = Column(String(20), default="geplant")
    notizen = Column(Text, nullable=True)
    custom_title = Column(String(255), nullable=True)
    custom_description = Column(Text, nullable=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    prioritaet = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    campaign = relationship("Campaign")

    def __repr__(self):
        return f"<MarketingIdeaTracker(idea={self.idea_number}, status='{self.status}')>"


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Settings(key='{self.key}')>"

class AgentTask(Base):
    __tablename__ = "agent_tasks"
    __table_args__ = (
        Index("ix_agent_tasks_status", "status"),
        Index("ix_agent_tasks_lead_id", "lead_id"),
        Index("ix_agent_tasks_agent", "assigned_to"),
        Index("ix_agent_tasks_lease_until", "lease_until"),
        Index("ix_agent_tasks_next_retry_at", "next_retry_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_type = Column(String(50), nullable=False)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    payload = Column(JSON, nullable=True)
    status = Column(String(20), default="pending")
    assigned_to = Column(String(100), nullable=True)
    lease_token = Column(String(64), nullable=True)
    lease_until = Column(DateTime, nullable=True)
    last_heartbeat_at = Column(DateTime, nullable=True)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=5)
    next_retry_at = Column(DateTime, nullable=True)
    result_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    lead = relationship("Lead")

    def __repr__(self):
        return f"<AgentTask(type='{self.task_type}', status='{self.status}')>"
