"""
Report Class
Generates comprehensive analysis reports for solar site selection

Dependencies:
- AnalysisRun: from analysis module
- SiteCandidate: from site module  
- StorageService: from storage module
- FileRef: from storage module
"""

from datetime import datetime
from typing import List
from uuid import UUID, uuid4


class Report:
    """
    Generate analysis reports for solar site selection
    
    Attributes:
        report_id: UUID - Unique report identifier
        date: datetime - Report generation date
        summary: string - Executive summary text
        file_path: string - Path to the generated report file
    
    Methods:
        generate(run:AnalysisRun, ranks:SiteCandidate[]) - Generate comprehensive report
        export(): FileRef - Export report as downloadable file
    """
    
    def __init__(self):
        """Initialize a new report"""
        self.report_id: UUID = uuid4()
        self.date: datetime = datetime.now()
        self.summary: str = ""
        self.file_path: str = ""
    
    def generate(self, run, ranks: List):
        """
        Generate comprehensive analysis report
        
        Args:
            run: AnalysisRun - Completed analysis run with metadata
            ranks: List[SiteCandidate] - Ranked list of site candidates
        
        This method creates a detailed report including:
        - Executive summary
        - Analysis methodology
        - Top site recommendations with scores
        - Environmental criteria breakdown
        - Maps and visualizations
        - Statistical analysis
        """
        # Generate executive summary
        if len(ranks) > 0:
            top_score = ranks[0].score
            self.summary = (
                f"Solar site analysis completed on {self.date.strftime('%Y-%m-%d')}. "
                f"Identified {len(ranks)} candidate sites. "
                f"Top site achieved suitability score of {top_score:.2f}."
            )
        else:
            self.summary = "No suitable sites identified in the analysis area."
        
        # Generate report content
        report_content = self._generate_report_content(run, ranks)
        
        # Set file path
        self.file_path = f"/reports/solar_analysis_{self.report_id}.pdf"
        
        # In a real implementation, this would:
        # 1. Create PDF/DOCX document using reportlab or python-docx
        # 2. Add report sections: title, summary, methodology, results
        # 3. Include charts and maps
        # 4. Add site recommendation tables
        # 5. Save to storage using StorageService
        
        print(f"✓ Report generated: {self.summary}")
        print(f"  Report ID: {self.report_id}")
        print(f"  File path: {self.file_path}")
    
    def export(self):
        """
        Export report as downloadable file
        
        Returns:
            FileRef - Reference to the exported report file
        
        The exported file can be:
        - PDF for final reports
        - DOCX for editable documents
        - HTML for web viewing
        """
        if not self.file_path:
            raise ValueError("Report must be generated before export. Call generate() first.")
        
        # Import FileRef from storage module
        # from storage_module import FileRef, StorageService
        
        # In a real implementation:
        # 1. Retrieve report from storage
        # 2. Prepare for download (compression, formatting)
        # 3. Return file reference with download URL
        
        # Placeholder: Create file reference
        # file_ref = FileRef(
        #     path=self.file_path,
        #     size=0,  # Would be actual file size
        #     content_type="application/pdf",
        #     url=f"/download/reports/{self.report_id}"
        # )
        
        print(f"✓ Report exported: {self.file_path}")
        # return file_ref
        return None  # Replace with actual FileRef when storage module is available
    
    # ========================================================================
    # PRIVATE HELPER METHODS
    # ========================================================================
    
    def _generate_report_content(self, run, ranks: List) -> str:
        """
        Generate detailed report content
        
        Args:
            run: Analysis run metadata (AnalysisRun)
            ranks: Ranked site candidates (List[SiteCandidate])
            
        Returns:
            Formatted report content as string
        """
        content = []
        
        # Title and metadata
        content.append("="*80)
        content.append("SOLAR SITE SELECTION ANALYSIS REPORT")
        content.append("="*80)
        content.append(f"\nReport ID: {self.report_id}")
        content.append(f"Generated: {self.date.strftime('%Y-%m-%d %H:%M:%S')}")
        content.append(f"Analysis Run: {run.run_id}")
        content.append(f"\n{'-'*80}\n")
        
        # Executive Summary
        content.append("EXECUTIVE SUMMARY")
        content.append("-"*80)
        content.append(self.summary)
        content.append(f"\n{'-'*80}\n")
        
        # Analysis Metadata
        content.append("ANALYSIS DETAILS")
        content.append("-"*80)
        content.append(f"Started: {run.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if run.finished_at:
            content.append(f"Finished: {run.finished_at.strftime('%Y-%m-%d %H:%M:%S')}")
        content.append(f"Duration: {run.duration_sec} seconds")
        content.append(f"Status: {run.status}")
        content.append(f"\n{'-'*80}\n")
        
        # Top Site Recommendations
        content.append("TOP SITE RECOMMENDATIONS")
        content.append("-"*80)
        
        if len(ranks) > 0:
            # Show top 10 sites
            top_sites = ranks[:min(10, len(ranks))]
            content.append(f"\nDisplaying top {len(top_sites)} of {len(ranks)} candidate sites:\n")
            
            for i, site in enumerate(top_sites, 1):
                content.append(f"{i}. Site ID: {site.site_id}")
                content.append(f"   Suitability Score: {site.score:.4f}")
                content.append(f"   Location: ({site.centroid.x:.4f}°E, {site.centroid.y:.4f}°N)")
                
                # Include environmental attributes if available
                if hasattr(site, 'attrs') and site.attrs:
                    content.append(f"   Attributes: {site.attrs}")
                content.append("")
        else:
            content.append("\nNo suitable sites identified.")
        
        content.append(f"{'-'*80}\n")
        
        # Statistical Summary
        if len(ranks) > 0:
            content.append("STATISTICAL SUMMARY")
            content.append("-"*80)
            
            scores = [site.score for site in ranks]
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            min_score = min(scores)
            
            content.append(f"Total Sites Evaluated: {len(ranks)}")
            content.append(f"Average Suitability Score: {avg_score:.4f}")
            content.append(f"Highest Score: {max_score:.4f}")
            content.append(f"Lowest Score: {min_score:.4f}")
            
            # Score distribution
            excellent = sum(1 for s in scores if s > 0.8)
            high = sum(1 for s in scores if 0.6 < s <= 0.8)
            moderate = sum(1 for s in scores if 0.4 < s <= 0.6)
            low = sum(1 for s in scores if s <= 0.4)
            
            content.append(f"\nScore Distribution:")
            content.append(f"  Excellent (>0.8):   {excellent:4d} sites ({excellent/len(ranks)*100:5.1f}%)")
            content.append(f"  High (0.6-0.8):     {high:4d} sites ({high/len(ranks)*100:5.1f}%)")
            content.append(f"  Moderate (0.4-0.6): {moderate:4d} sites ({moderate/len(ranks)*100:5.1f}%)")
            content.append(f"  Low (<0.4):         {low:4d} sites ({low/len(ranks)*100:5.1f}%)")
            
            content.append(f"\n{'-'*80}\n")
        
        # Methodology
        content.append("METHODOLOGY")
        content.append("-"*80)
        content.append("Analysis conducted using:")
        content.append("- UAV photogrammetry and high-resolution imagery")
        content.append("- YOLOv8 AI-powered object detection")
        content.append("- AHP (Analytical Hierarchy Process) multi-criteria evaluation")
        content.append("- Environmental data layers:")
        content.append("  • Global Horizontal Irradiance (GHI)")
        content.append("  • Terrain Slope")
        content.append("  • Land Surface Temperature (LST)")
        content.append("  • Elevation")
        content.append("  • Sunshine Hours")
        content.append(f"\n{'-'*80}\n")
        
        # Footer
        content.append("="*80)
        content.append("End of Report")
        content.append("="*80)
        
        return "\n".join(content)
    
    def __str__(self):
        """String representation of report"""
        return f"Report(id={self.report_id}, date={self.date.strftime('%Y-%m-%d')}, summary='{self.summary[:50]}...')"
    
    def __repr__(self):
        """Developer representation"""
        return f"Report(report_id={self.report_id}, date={self.date}, file_path={self.file_path!r})"
