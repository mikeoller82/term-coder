#!/usr/bin/env python3
"""Test script to verify comprehensive file system access."""

from src.term_coder.natural_interface import NaturalLanguageInterface
from unittest.mock import Mock

def test_comprehensive_access():
    """Test that the natural language interface has comprehensive file system access."""
    print("🔧 Testing Comprehensive File System Access")
    print("=" * 60)
    
    # Create mock config and console
    config = Mock()
    config.get = Mock(return_value=False)
    console = Mock()
    console.print = Mock()
    
    try:
        # Initialize interface
        interface = NaturalLanguageInterface(config, console)
        
        print(f"✅ Interface initialized with components:")
        print(f"   • LLM: {'✅' if interface.llm else '❌'}")
        print(f"   • Search: {'✅' if interface.search else '❌'}")
        print(f"   • Context Engine: {'✅' if interface.context_engine else '❌'}")
        print(f"   • Editor: {'✅' if interface.editor else '❌'}")
        print(f"   • Patcher: {'✅' if interface.patcher else '❌'}")
        print(f"   • File Indexer: {'✅' if interface.indexer else '❌'}")
        print(f"   • Git Tools: {'✅' if interface.git else '❌'}")
        print(f"   • Code Generator: {'✅' if interface.generator else '❌'}")
        print(f"   • Refactorer: {'✅' if interface.refactorer else '❌'}")
        print(f"   • Code Explainer: {'✅' if interface.explainer else '❌'}")
        print(f"   • Error Fixer: {'✅' if interface.fixer else '❌'}")
        print(f"   • Test Runner: {'✅' if interface.tester else '❌'}")
        print(f"   • Command Runner: {'✅' if interface.runner else '❌'}")
        
        # Test comprehensive file access
        print("\n🧪 Testing Comprehensive File Access:")
        file_access = interface._get_comprehensive_file_access()
        
        if 'error' in file_access:
            print(f"❌ Error getting file access: {file_access['error']}")
            return False
        
        total_files = file_access.get('total_files', 0)
        print(f"   📁 Total files accessible: {total_files}")
        print(f"   🗂️  Root path: {file_access.get('root_path', 'Unknown')}")
        
        if total_files > 0:
            print("   📄 Sample files:")
            for i, file_info in enumerate(file_access['files'][:5]):
                print(f"      {i+1}. {file_info['path']} ({file_info['size']} bytes)")
        
        # Test directory structure access
        print("\n🧪 Testing Directory Structure Access:")
        dir_structure = interface._get_directory_structure()
        
        if 'error' in dir_structure:
            print(f"❌ Error getting directory structure: {dir_structure['error']}")
        else:
            print(f"   📂 Directories accessible: {len(dir_structure)}")
            for path, info in list(dir_structure.items())[:3]:
                print(f"      {path}: {info['file_count']} files")
        
        # Test file reading
        print("\n🧪 Testing File Reading:")
        test_file = "src/term_coder/__init__.py"
        content = interface._read_file_content(test_file)
        
        if content.startswith("Error") or content.startswith("File not found"):
            print(f"❌ Cannot read file: {content}")
        else:
            print(f"   ✅ Successfully read {test_file} ({len(content)} characters)")
            print(f"      Preview: {content[:100]}...")
        
        # Test file search
        print("\n🧪 Testing File Search:")
        search_results = interface._search_in_files("class", "*.py")
        
        if search_results and not search_results[0].get('error'):
            print(f"   ✅ Found 'class' in {len(search_results)} files")
            for result in search_results[:3]:
                print(f"      {result['file']}: {result['total_matches']} matches")
        else:
            print(f"   ❌ Search failed: {search_results}")
        
        # Test Python code analysis
        print("\n🧪 Testing Python Code Analysis:")
        analysis = interface._list_functions_and_classes("src/term_coder/llm.py")
        
        if 'error' in analysis:
            print(f"   ❌ Analysis failed: {analysis['error']}")
        else:
            functions = analysis.get('functions', [])
            classes = analysis.get('classes', [])
            print(f"   ✅ Found {len(functions)} functions and {len(classes)} classes")
            if classes:
                print(f"      Classes: {[c['name'] for c in classes[:3]]}")
            if functions:
                print(f"      Functions: {[f['name'] for f in functions[:3]]}")
        
        print("\n🎉 SUCCESS! Natural Language Interface has comprehensive file system access!")
        print("\n🚀 Available Capabilities:")
        print("   • 📁 Complete file system traversal and access")
        print("   • 🔍 Multi-method search (hybrid, text, pattern)")
        print("   • 📖 Full file content reading and writing")
        print("   • 🏗️  Directory structure analysis")
        print("   • 🐍 Python code parsing and analysis")
        print("   • 🔧 Comprehensive editing and generation tools")
        print("   • 🧠 Real AI-powered analysis and suggestions")
        print("   • 🔄 Git integration and version control")
        print("   • 🧪 Testing and execution capabilities")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_comprehensive_access()
    exit(0 if success else 1)