#!/usr/bin/env python3
"""
Weak Topics Analyzer for OpenClaw Job Hunt Brain Study Engine
Identifies topics that need attention based on performance metrics
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

def analyze_weak_topics():
    """Analyze and identify weak topics from study performance"""
    data_file = Path("~/.jarvis/automations/job-automation/output/study_topics.json").expanduser()
    daily_file = Path("~/.jarvis/automations/job-automation/output/daily_questions.json").expanduser()
    
    # Load study topics data
    if not data_file.exists():
        print("❌ No study topics found. Run study_engine.py with --add-samples first.")
        return None
    
    with open(data_file, 'r') as f:
        study_data = json.load(f)
    
    topics = study_data.get("topics", {})
    
    # Load today's daily questions for additional context
    daily_analysis = None
    if daily_file.exists():
        with open(daily_file, 'r') as f:
            daily_analysis = json.load(f)
    
    weak_topics = []
    
    # Analyze each topic for weakness
    for deck_name, topic_data in topics.items():
        mastery_score = topic_data.get("mastery_score", 0.0)
        review_count = topic_data.get("review_count", 0)
        success_count = topic_data.get("success_count", 0)
        last_reviewed = topic_data.get("last_reviewed")
        
        # Calculate performance metrics
        success_rate = (success_count / review_count * 100) if review_count > 0 else 0.0
        
        # Determine weakness level
        weakness_score = 0.0
        issues = []
        
        # Low mastery score (below 3.0 out of 5.0)
        if mastery_score < 3.0:
            weakness_score += (3.0 - mastery_score) * 10
            issues.append(f"Low mastery score ({mastery_score}/5.0)")
        
        # Low success rate (below 60%)
        if success_rate < 60.0:
            weakness_score += (60.0 - success_rate) * 0.5
            issues.append(f"Low success rate ({success_rate:.1f}%)")
        
        # Few reviews (less than 3)
        if review_count < 3:
            weakness_score += (3.0 - review_count) * 5
            issues.append(f"Insufficient reviews ({review_count}/3)")
        
        # Long time since last review
        if last_reviewed:
            try:
                last_date = datetime.fromisoformat(last_reviewed)
                days_since = (datetime.now() - last_date).days
                if days_since > 7:
                    weakness_score += days_since * 0.5
                    issues.append(f"Not reviewed in {days_since} days")
            except (ValueError, TypeError):
                pass
        
        # Only include topics with significant weakness
        if weakness_score >= 5.0:
            weak_topics.append({
                "deck": deck_name,
                "name": topic_data.get("name", deck_name),
                "mastery_score": mastery_score,
                "success_rate": success_rate,
                "review_count": review_count,
                "weakness_score": weakness_score,
                "issues": issues,
                "priority": "high" if weakness_score >= 15.0 else "medium"
            })
    
    # Sort by weakness score (descending)
    weak_topics.sort(key=lambda x: x["weakness_score"], reverse=True)
    
    # Add daily analysis insights if available
    if daily_analysis:
        daily_weak_topics = daily_analysis.get("weak_topics", [])
        for daily_topic in daily_weak_topics:
            # Check if this topic is already in weak_topics
            existing = next((t for t in weak_topics if t["deck"] == daily_topic["deck"]), None)
            if existing:
                # Add daily context to existing entry
                existing["daily_issues"] = daily_topic.get("issues", [])
            else:
                # Add new topic with daily context
                weak_topics.append({
                    "deck": daily_topic["deck"],
                    "name": daily_topic["name"],
                    "mastery_score": daily_topic.get("mastery_score", 0.0),
                    "success_rate": daily_topic.get("success_rate", 0.0),
                    "review_count": daily_topic.get("review_count", 0),
                    "weakness_score": daily_topic.get("weakness_score", 0.0),
                    "issues": daily_topic.get("issues", []),
                    "priority": "high",
                    "daily_issues": True
                })
    
    # Save analysis results
    output_file = Path("~/.jarvis/automations/job-automation/output/weak_topics_analysis.json").expanduser()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    analysis_result = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "total_topics_analyzed": len(topics),
        "weak_topics_count": len(weak_topics),
        "weak_topics": weak_topics,
        "generated_at": datetime.now().isoformat(),
        "recommendations": []
    }
    
    # Add recommendations
    if weak_topics:
        high_priority = [t for t in weak_topics if t["priority"] == "high"]
        if high_priority:
            analysis_result["recommendations"].append(
                f"Focus on {len(high_priority)} high-priority topics today"
            )
        
        # Suggest specific actions based on issues
        for topic in weak_topics[:3]:  # Top 3 recommendations
            if "Low mastery score" in topic.get("issues", []):
                analysis_result["recommendations"].append(
                    f"Review {topic['name']} fundamentals - mastery is {topic['mastery_score']}/5.0"
                )
                break
    
    with open(output_file, 'w') as f:
        json.dump(analysis_result, f, indent=2)
    
    return analysis_result

def main():
    """Main function to run the weak topics analyzer"""
    print("🔍 Analyzing weak topics for study optimization...")
    print("=" * 50)
    
    analysis = analyze_weak_topics()
    
    if analysis is None:
        return
    
    # Display results
    print(f"\n📊 Weak Topics Analysis for {analysis['date']}")
    print(f"📝 Topics Analyzed: {analysis['total_topics_analyzed']}")
    print(f"⚠️  Weak Topics Found: {analysis['weak_topics_count']}")
    print(f"💡 Recommendations: {len(analysis['recommendations'])}")
    
    if analysis['weak_topics']:
        print(f"\n🔴 TOP WEAK TOPICS:")
        for i, topic in enumerate(analysis['weak_topics'][:5], 1):  # Show top 5
            print(f"\n{i}. {topic['name']} ({topic['deck']})")
            print(f"   🎯 Mastery: {topic['mastery_score']}/5.0 | Success Rate: {topic['success_rate']:.1f}%")
            print(f"   📚 Reviews: {topic['review_count']} | Priority: {topic['priority']}")
            print(f"   ⚠️  Issues: {', '.join(topic.get('issues', []))}")
        
        # Show recommendations
        if analysis['recommendations']:
            print(f"\n💡 KEY RECOMMENDATIONS:")
            for i, rec in enumerate(analysis['recommendations'], 1):
                print(f"   {i}. {rec}")
        
        print(f"\n🚀 Action Plan:")
        print(f"   - Review weak topics with highest priority first")
        print(f"   - Focus on topics with low mastery scores")
        print(f"   - Revisit topics with low success rates")
        print(f"   - Schedule follow-up reviews for topics not recently covered")
    
    print(f"\n✅ Analysis complete. Results saved to: {analysis.get('analysis_file', 'weak_topics_analysis.json')}")

if __name__ == "__main__":
    main()