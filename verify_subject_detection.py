import sys
import os

# Ensure app is in path
sys.path.append(os.getcwd())

from app.rag.subject_detector import detect_subject

test_cases = [
    {
        "name": "Python Theory",
        "text": """
        Python is a high-level, general-purpose programming language. Its design philosophy emphasizes code readability with the use of significant indentation.
        Lists, tuples, dictionaries, and sets are built-in data structures.
        def factorial(n):
            if n == 0: return 1
            return n * factorial(n-1)
        Pandas and Numpy are used for data analysis.
        """,
        "expected": "Python Programming"
    },
    {
        "name": "Physics Lab",
        "text": """
        Engineering Physics Laboratory Manual.
        Experiment No. 1: Determination of Wavelength of a Laser Source.
        Aim: To determine the wavelength of given laser source using diffraction grating.
        Apparatus: Laser source, grating, screen.
        Procedure: Set up the optical bench...
        """,
        "expected": "Applied Physics Lab",
        "expected_type": "lab"
    },
    {
        "name": "DBMS",
        "text": """
        A Relational Database Management System (RDBMS) is a database management system based on the relational model.
        Normalization is the process of organizing data in a database.
        SQL (Structured Query Language) is used to communicate with a database.
        ACID properties: Atomicity, Consistency, Isolation, Durability.
        """,
        "expected": "Database Management Systems"
    },
    {
        "name": "Math - Calculus",
        "text": """
        Differential Equations and Vector Calculus.
        Solve the linear differential equation dy/dx + P(x)y = Q(x).
        Eigenvalues and Eigenvectors of a matrix.
        Cayley-Hamilton Theorem.
        """,
        "expected": "Mathematics–I" 
        # Note: Depending on keywords, could be Math-I or Math-II. System should pick one with high confidence.
    },
    {
        "name": "Ambiguous / Mixed",
        "text": """
        Introduction to Artificial Intelligence and Machine Learning.
        We will study search algorithms like A* and Minimax.
        We will also look at Neural Networks and Backpropagation.
        Supervised learning vs Unsupervised learning.
        """,
        "expected_ambiguous": True
    }
]

print("=== Running Subject Detector Verification ===")
for case in test_cases:
    print(f"\nTest: {case['name']}")
    result = detect_subject(case['text'])
    print(f"Predicted Subject: {result.subject}")
    print(f"Confidence: {result.confidence:.2f}")
    print(f"Type: {result.content_type}")
    print(f"Ambiguous: {result.is_ambiguous}")
    if result.secondary_subject:
        print(f"Secondary: {result.secondary_subject}")
    
    # Assertions
    if 'expected' in case:
        if result.subject == case['expected']:
            print("✅ Subject Match")
        else:
            print(f"❌ Subject Mismatch (Expected: {case['expected']})")
    
    if 'expected_type' in case:
        if result.content_type == case['expected_type']:
            print("✅ Type Match")
        else:
             print(f"❌ Type Mismatch (Expected: {case['expected_type']})")

    if 'expected_ambiguous' in case:
        if result.is_ambiguous:
             print("✅ Ambiguity Detected")
        else:
             print("⚠️ Ambiguity NOT Detected (Might be certain enough)")

print("\n=== Verification Complete ===")
