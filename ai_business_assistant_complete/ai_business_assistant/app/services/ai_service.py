import os
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.schema import HumanMessage, SystemMessage
from app.core.config import settings


def get_llm():
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=settings.TEMPERATURE,
        openai_api_key=settings.OPENAI_API_KEY,
    )


def generate_marketing_content(business_type: str, goal: str) -> str:
    """Generate marketing content for a business using LLM."""
    llm = get_llm()

    prompt = PromptTemplate(
        input_variables=["business_type", "goal"],
        template="""You are an expert marketing strategist and copywriter.

Business Type: {business_type}
Marketing Goal: {goal}

Create compelling marketing content that includes:
1. A catchy headline
2. A short tagline (under 10 words)
3. A 3-sentence elevator pitch
4. 3 key value propositions
5. A call-to-action

Be specific, persuasive, and tailored to the business type."""
    )

    chain = LLMChain(llm=llm, prompt=prompt)
    result = chain.run(business_type=business_type, goal=goal)
    return result


def generate_business_plan_section(
    business_type: str,
    section: str,
    context: str = ""
) -> str:
    """Generate a specific section of a business plan."""
    llm = get_llm()

    messages = [
        SystemMessage(content=(
            "You are a seasoned business consultant with expertise in "
            "startups, strategy, and market analysis. Provide detailed, "
            "actionable, and professional business advice."
        )),
        HumanMessage(content=(
            f"Business Type: {business_type}\n"
            f"Section to write: {section}\n"
            f"Additional context: {context}\n\n"
            f"Write a comprehensive {section} section for this business. "
            "Be specific with metrics, timelines, and strategies where possible."
        ))
    ]

    response = llm.invoke(messages)
    return response.content


def analyze_competitors(business_type: str, market: str) -> str:
    """Analyze competition for a given business in a market."""
    llm = get_llm()

    prompt = PromptTemplate(
        input_variables=["business_type", "market"],
        template="""You are a market research analyst.

Analyze the competitive landscape for a {business_type} business targeting the {market} market.

Provide:
1. Top 3-5 likely competitors (or competitor types)
2. Their key strengths and weaknesses
3. Market gaps and opportunities
4. Recommended differentiation strategies
5. Pricing positioning advice

Be analytical and data-driven in your response."""
    )

    chain = LLMChain(llm=llm, prompt=prompt)
    return chain.run(business_type=business_type, market=market)


def generate_social_media_posts(
    business_type: str,
    platform: str,
    topic: str,
    count: int = 3
) -> list[str]:
    """Generate social media posts for a business."""
    llm = get_llm()

    messages = [
        SystemMessage(content=(
            f"You are a social media expert specializing in {platform} content. "
            "Create engaging, platform-appropriate posts with relevant hashtags."
        )),
        HumanMessage(content=(
            f"Create {count} {platform} posts for a {business_type} business about: {topic}\n\n"
            f"Format each post clearly numbered (1., 2., 3.). "
            f"Include appropriate hashtags and emojis for {platform}."
        ))
    ]

    response = llm.invoke(messages)
    # Split posts by numbered pattern
    content = response.content
    posts = [p.strip() for p in content.split('\n\n') if p.strip()]
    return posts if len(posts) >= count else [content]
