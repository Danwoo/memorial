import { Loader2, FileBarChart } from 'lucide-react'
import type { ReportData } from '../../api/reports'

interface ReportTabProps {
  report: ReportData | null
  loading: boolean
}

export default function ReportTab({ report, loading }: ReportTabProps) {
  if (loading) {
    return (
      <div className="report-loading">
        <Loader2 size={24} className="spinning" />
        <p>AI 리포트를 생성하고 있습니다...</p>
      </div>
    )
  }
  if (!report) {
    return (
      <div className="report-loading">
        <p>데이터가 부족합니다.</p>
      </div>
    )
  }
  return (
    <div className="report-content">
      <div className="report-hero">
        <div className="report-hero-header">
          <FileBarChart size={20} />
          <span className="report-period">{report.date_range}</span>
        </div>
        <p className="report-summary">{report.llm_summary}</p>
        <div className="report-stats-row">
          <div className="report-stat">
            <span className="report-stat-num">{report.total_memories}</span>
            <span className="report-stat-label">스크랩</span>
          </div>
          <div className="report-stat">
            <span className="report-stat-num">{report.total_journals}</span>
            <span className="report-stat-label">다이어리</span>
          </div>
          <div className="report-stat">
            <span className="report-stat-num">{report.topic_distribution.length}</span>
            <span className="report-stat-label">주제</span>
          </div>
        </div>
      </div>

      {report.highlights.length > 0 && (
        <div className="report-highlights">
          <h3>하이라이트</h3>
          <ul>
            {report.highlights.map((h, i) => (
              <li key={i}>{h}</li>
            ))}
          </ul>
        </div>
      )}

      {report.topic_distribution.length > 0 && (
        <div className="report-topics">
          <h3>주제 분포</h3>
          <div className="report-topic-bars">
            {report.topic_distribution.map(t => (
              <div key={t.topic} className="report-topic-item">
                <span className="report-topic-name">#{t.topic}</span>
                <div className="report-topic-bar">
                  <div
                    className="report-topic-bar-fill"
                    style={{ width: `${t.percentage}%` }}
                  />
                </div>
                <span className="report-topic-pct">{t.percentage}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {report.source_distribution.length > 0 && (
        <div className="report-sources">
          <h3>소스 분포</h3>
          <div className="report-source-chips">
            {report.source_distribution.map(s => (
              <span key={s.source_type} className="report-source-chip">
                {s.source_type} ({s.count})
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
