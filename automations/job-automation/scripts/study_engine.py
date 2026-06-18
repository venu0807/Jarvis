#!/usr/bin/env python3
"""
Study Engine for OpenClaw Job Hunt Brain
Handles spaced repetition, topic management, and question generation
"""

import json
import argparse
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

# Define study decks based on Venu's profile
STUDY_DECKS = {
    "DSA": {
        "name": "Data Structures & Algorithms",
        "difficulty_levels": {
            "easy": 3.0,
            "medium": 4.0,
            "hard": 5.0
        },
        "sample_questions": [
            "Implement a binary search tree with insert and search operations",
            "Explain the difference between BFS and DFS traversal algorithms",
            "Design an LRU cache implementation with O(1) operations",
            "Analyze the time complexity of quicksort in best/worst cases",
            "Implement a graph using adjacency list and adjacency matrix"
        ]
    },
    "Android": {
        "name": "Android Development",
        "difficulty_levels": {
            "easy": 2.5,
            "medium": 3.5,
            "hard": 4.5
        },
        "sample_questions": [
            "Explain Activity lifecycle and when to override each callback",
            "Implement a custom View with custom drawing logic",
            "Work with RecyclerView and custom adapters",
            "Implement background services and foreground services",
            "Handle permissions and runtime permission requests"
        ]
    },
    "ML_AI": {
        "name": "Machine Learning & AI",
        "difficulty_levels": {
            "easy": 3.5,
            "medium": 4.5,
            "hard": 5.5
        },
        "sample_questions": [
            "Explain different types of ML algorithms (supervised, unsupervised, reinforcement)",
            "Implement a simple neural network from scratch",
            "Explain concepts of overfitting, underfitting, and regularization",
            "Work with scikit-learn for classification and regression",
            "Explain feature engineering and data preprocessing"
        ]
    },
    "SystemDesign": {
        "name": "System Design",
        "difficulty_levels": {
            "easy": 3.0,
            "medium": 4.0,
            "hard": 5.0
        },
        "sample_questions": [
            "Design a URL shortening service like bit.ly",
            "Design a chat application or messaging system",
            "Design a recommendation system",
            "Design a load balancer and content delivery network",
            "Design a database sharding strategy"
        ]
    },
    "Java": {
        "name": "Java Programming",
        "difficulty_levels": {
            "easy": 2.0,
            "medium": 3.0,
            "hard": 4.0
        },
        "sample_questions": [
            "Explain Java memory model and garbage collection",
            "Implement multithreading using threads and executors",
            "Work with collections framework and streams API",
            "Explain Java 8+ features (Optional, Stream, Functional)",
            "Implement exception handling and custom exceptions"
        ]
    }
}

def add_sample_topics():
    """Add sample topics to the study engine"""
    data_file = Path("~/.jarvis/automations/job-automation/output/study_topics.json").expanduser()
    
    # Create output directory if it doesn't exist
    data_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize or load existing data
    if data_file.exists():
        with open(data_file, 'r') as f:
            data = json.load(f)
    else:
        data = {
            "topics": {},
            "last_updated": datetime.now().isoformat(),
            "decks": list(STUDY_DECKS.keys())
        }
    
    # Add sample topics if not already present
    topics_added = []
    for deck_name, deck_info in STUDY_DECKS.items():
        if deck_name not in data["topics"]:
            data["topics"][deck_name] = {
                "name": deck_info["name"],
                "difficulty_levels": deck_info["difficulty_levels"],
                "questions": deck_info["sample_questions"],
                "mastery_score": 0.0,
                "last_reviewed": None,
                "next_review": datetime.now().isoformat(),
                "review_count": 0,
                "success_count": 0
            }
            topics_added.append(deck_name)
    
    data["last_updated"] = datetime.now().isoformat()
    
    with open(data_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    if topics_added:
        print(f"✅ Added sample topics for decks: {', '.join(topics_added)}")
    else:
        print("✅ Sample topics already exist - no topics added")

def generate_daily_questions():
    """Generate daily study questions based on spaced repetition"""
    data_file = Path("~/.jarvis/automations/job-automation/output/study_topics.json").expanduser()
    
    if not data_file.exists():
        print("❌ No study topics found. Run with --add-samples first.")
        return
    
    with open(data_file, 'r') as f:
        data = json.load(f)
    
    questions = []
    weak_topics = []
    
    # Generate questions based on mastery scores and review counts
    for deck_name, deck_info in data.get("topics", {}).items():
        mastery_score = deck_info.get("mastery_score", 0.0)
        review_count = deck_info.get("review_count", 0)
        
        # Prioritize topics with low mastery scores
        if mastery_score < 3.0 or review_count < 3:
            weak_topics.append({
                "deck": deck_name,
                "name": deck_info["name"],
                "mastery_score": mastery_score,
                "review_count": review_count,
                "priority": "high" if mastery_score < 2.5 else "medium"
            })
        
        # Get a question from this deck
        questions_list = deck_info.get("questions", [])
        if questions_list:
            question = {
                "deck": deck_name,
                "name": deck_info["name"],
                "question": questions_list[review_count % len(questions_list)],
                "difficulty": "medium",  # Default to medium, could be refined
                "mastery_score": mastery_score,
                "review_count": review_count,
                "timestamp": datetime.now().isoformat()
            }
            questions.append(question)
    
    # Sort questions by priority and mastery score
    questions.sort(key=lambda x: (x["mastery_score"], x["review_count"]))
    weak_topics.sort(key=lambda x: (x["mastery_score"], x["review_count"]))
    
    # Save today's questions
    output_file = Path("~/.jarvis/automations/job-automation/output/daily_questions.json").expanduser()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    daily_data = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "questions": questions,
        "weak_topics": weak_topics,
        "generated_at": datetime.now().isoformat(),
        "total_questions": len(questions),
        "weak_topics_count": len(weak_topics)
    }
    
    with open(output_file, 'w') as f:
        json.dump(daily_data, f, indent=2)
    
    # Display results
    print(f"\n📚 Daily Study Questions for {daily_data['date']}")
    print(f"📝 Total Questions: {daily_data['total_questions']}")
    print(f"⚠️  Weak Topics: {daily_data['weak_topics_count']}")
    
    for i, question in enumerate(questions[:5], 1):  # Show first 5 questions
        print(f"\n{i}. {question['name']} ({question['difficulty']})")
        print(f"   Q: {question['question']}")
        print(f"   Mastery: {question['mastery_score']}/5.0 | Reviews: {question['review_count']}")
    
    if weak_topics:
        print(f"\n⚠️  WEAK TOPICS (Focus on these):")
        for i, topic in enumerate(weak_topics, 1):
            print(f"   {i}. {topic['name']} - Mastery: {topic['mastery_score']}/5.0 | Reviews: {topic['review_count']}")
    
    return daily_data

def main():
    parser = argparse.ArgumentParser(description="Study Engine for OpenClaw Job Hunt Brain")
    parser.add_argument("--add-samples", action="store_true", help="Add sample study topics")
    parser.add_argument("--message", action="store_true", help="Generate daily study questions")
    
    args = parser.parse_args()
    
    if args.add_samples:
        add_sample_topics()
    
    if args.message:
        generate_daily_questions()

if __name__ == "__main__":
    main()