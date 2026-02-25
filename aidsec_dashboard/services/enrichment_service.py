import logging
from datetime import datetime
from database.database import get_session
from database.models import Lead, LeadEnrichment
from services.scraper_service import get_scraper_service
from services.ranking_service import get_ranking_service

logger = logging.getLogger(__name__)

def enrich_lead(lead_id: int):
    """
    Background task to automatically scrape website data, run security checks, 
    and save the results to the LeadEnrichment table.
    """
    logger.info(f"Starting enrichment for lead_id: {lead_id}")
    
    with get_session() as db:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            logger.error(f"Cannot enrich: Lead {lead_id} not found.")
            return

        if not lead.website:
            logger.warning(f"Cannot enrich: Lead {lead_id} has no website.")
            return

        # Initialize or get existing enrichment record
        enrichment = db.query(LeadEnrichment).filter(LeadEnrichment.lead_id == lead.id).first()
        if not enrichment:
            enrichment = LeadEnrichment(lead_id=lead.id)
            db.add(enrichment)

        lead.research_status = "in_progress"
        db.commit()

        try:
            # 1. Scrape Website for Text
            scraper = get_scraper_service()
            scraped_data = scraper.scrape_company_info(lead.website)
            
            enrichment.about_us = scraped_data.get("about_us")
            enrichment.mission_statement = scraped_data.get("mission_statement")
            
            # 2. Run Advanced Ranking / Security Checks
            ranker = get_ranking_service()
            ranking_data = ranker.check_url(lead.website)
            
            # Update core lead ranking stats mapping
            lead.ranking_score = ranking_data.get("score")
            lead.ranking_grade = ranking_data.get("grade")
            lead.ranking_details = ranking_data.get("headers")
            lead.ranking_checked_at = datetime.utcnow()
            
            # Update advanced tracking
            enrichment.ssl_valid = ranking_data.get("ssl_valid")
            enrichment.cms_detected = ranking_data.get("cms_detected")
            
            # Finalize Status
            lead.research_status = "completed"
            lead.research_last = datetime.utcnow()
            
            db.commit()
            logger.info(f"Successfully enriched lead_id: {lead_id}")
            
        except Exception as e:
            logger.error(f"Failed to enrich lead_id: {lead_id} - Error: {e}")
            lead.research_status = "failed"
            db.commit()
