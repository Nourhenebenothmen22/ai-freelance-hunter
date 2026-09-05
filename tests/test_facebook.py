"""Tests for Facebook Group Scraper Adapter."""

import pytest
from src.adapters.facebook_adapter import FacebookGroupAdapter


@pytest.fixture
def facebook_adapter():
    cfg = {
        "source": "facebook_freelance_tn",
        "name": "Facebook Freelance Tunisie",
        "group_name": "Freelance Tunisie",
        "url": "https://www.facebook.com/groups/freelance.tunisie.it/",
        "enabled": True
    }
    return FacebookGroupAdapter(cfg)


def test_contact_extraction():
    sample_text = (
        "Besoin urgent d'un développeur React Node.js pour un projet freelance.\n"
        "Envoyez CV par email: contact@techagency.tn ou dev.freelance@gmail.com\n"
        "Contact par téléphone: +216 98 123 456 ou 20123456\n"
        "WhatsApp: https://wa.me/21698123456"
    )
    contacts = FacebookGroupAdapter.extract_contacts(sample_text)
    
    assert "contact@techagency.tn" in contacts["emails"]
    assert "dev.freelance@gmail.com" in contacts["emails"]
    assert len(contacts["phones"]) >= 1
    assert any("21698123456" in w for w in contacts["whatsapp"])


def test_facebook_post_normalization(facebook_adapter):
    raw_post = {
        "title": "Cherche développeur Full Stack React / Next.js pour mission freelance",
        "description": "Bonjour, nous cherchons un dev React pour finaliser un SaaS. Projet 1 mois. Tél: 98123456 à Tunis.",
        "url": "https://www.facebook.com/groups/freelance.tunisie/permalink/123456789/",
        "author": "Karim Ben Salah"
    }
    normalized = facebook_adapter.normalize(raw_post)
    
    assert "React" in normalized["title"]
    assert normalized["freelance"] is True
    assert normalized["location"] == "Tunisia / Remote"
    assert "Karim Ben Salah" in normalized["company"]
    assert "98123456" in normalized["description"]
    assert normalized["source"] == "facebook_freelance_tn"


@pytest.mark.asyncio
async def test_facebook_failure_isolation(facebook_adapter):
    """When Facebook presents a login wall or block, adapter must return empty list safely."""
    # run_safe must NOT throw exception
    items, err = await facebook_adapter.run_safe()
    assert isinstance(items, list)
