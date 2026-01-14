'use client'

import { useState } from 'react'
import { Solution } from '@/types'
import { Sparkles, FileText, Lightbulb, Brain, Settings, Star, RotateCw, ChevronDown, ChevronUp } from 'lucide-react'

interface SolutionViewProps {
  solution: Solution
  onRegenerate?: () => void
  isRegenerating?: boolean
}

// Clean markdown formatting from text
const cleanMarkdown = (text: string): string => {
  if (!text) return text
  return text
    .replace(/\*\*\*(.+?)\*\*\*/g, '$1')
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/_{3}(.+?)_{3}/g, '$1')
    .replace(/__(.+?)__/g, '$1')
    .replace(/_(.+?)_/g, '$1')
}

export default function SolutionView({ solution, onRegenerate, isRegenerating = false }: SolutionViewProps) {
  const [feedbackRating, setFeedbackRating] = useState(solution?.feedback_rating || 0)
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false)

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const handleFeedbackRating = (rating: number) => {
    setFeedbackRating(rating)
    // TODO: Send rating to API
    console.log('Rating submitted:', rating)
  }

  return (
    <div className="bg-card rounded-xl shadow-sm border border-border overflow-hidden mt-6">
      {/* Header */}
      <div className="px-6 py-4 border-b border-border bg-gradient-to-r from-primary/5 to-secondary/5">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-primary to-secondary rounded-lg flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
                AI-Generated Solution
                {solution.ai_model_used?.includes('groq') || solution.ai_model_used?.includes('llama') ? (
                  <span className="text-xs font-normal px-2 py-0.5 bg-secondary/10 text-secondary rounded-full">
                    🖥️ Free Local Model
                  </span>
                ) : null}
              </h2>
              <p className="text-sm text-muted-foreground">
                {solution.ai_model_used || solution.model_used} • Confidence: {Math.round((solution.confidence_score || 0) * 100)}%
              </p>
            </div>
          </div>
          {onRegenerate && (
            <button
              onClick={onRegenerate}
              disabled={isRegenerating}
              className="flex items-center gap-2 px-4 py-2 bg-primary/10 hover:bg-primary/20 disabled:bg-muted text-primary border border-primary/20 rounded-lg text-sm font-medium transition-all"
              title="Generate a new solution"
            >
              <RotateCw className={`h-4 w-4 ${isRegenerating ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">{isRegenerating ? 'Regenerating...' : 'Regenerate'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Content - Unified View */}
      <div className="px-6 py-8 space-y-8">
        {/* Solution Section */}
        <section>
          <div className="flex items-center space-x-2 mb-4">
            <FileText className="w-5 h-5 text-primary" />
            <h3 className="text-xl font-semibold text-foreground">Solution</h3>
          </div>
          <div className="prose prose-sm max-w-none text-foreground/90">
            <div className="whitespace-pre-wrap leading-relaxed">
              {cleanMarkdown(solution.content)}
            </div>
          </div>
        </section>

        {/* Explanation Section - Integrated */}
        {solution.explanation && (
          <section className="bg-primary/5 rounded-lg p-6 border border-primary/10">
            <div className="flex items-center space-x-2 mb-4">
              <Lightbulb className="w-5 h-5 text-primary" />
              <h3 className="text-lg font-semibold text-foreground">How It Works</h3>
            </div>
            <div className="prose prose-sm max-w-none text-foreground/80">
              <div className="whitespace-pre-wrap leading-relaxed">
                {cleanMarkdown(solution.explanation)}
              </div>
            </div>
          </section>
        )}

        {/* Step-by-Step - Inline */}
        {solution.step_by_step && solution.step_by_step.length > 0 && (
          <section>
            <div className="flex items-center space-x-2 mb-4">
              <FileText className="w-5 h-5 text-secondary" />
              <h3 className="text-lg font-semibold text-foreground">Step-by-Step Walkthrough</h3>
            </div>
            <div className="space-y-3">
              {solution.step_by_step.map((stepObj, index) => {
                const stepText = typeof stepObj === 'string' ? stepObj : stepObj.step
                const explanation = typeof stepObj === 'object' && stepObj.explanation ? stepObj.explanation : ''
                
                if (!stepText || stepText.trim() === '') return null
                
                const isHeader = stepText.startsWith('Problem') || (stepText.includes(':') && !stepText.startsWith('Step'))
                
                return (
                  <div
                    key={index}
                    className={`${
                      isHeader
                        ? 'bg-secondary/5 border-l-4 border-secondary p-4 rounded-r-lg'
                        : 'bg-muted/50 p-4 rounded-lg ml-4'
                    }`}
                  >
                    <div className={`${isHeader ? 'font-semibold text-secondary' : 'text-foreground/80'}`}>
                      {!isHeader && <span className="text-primary font-semibold mr-2">{index + 1}.</span>}
                      {cleanMarkdown(stepText)}
                    </div>
                    {explanation && (
                      <div className="mt-2 text-sm text-muted-foreground ml-4">
                        {cleanMarkdown(explanation)}
                      </div>
                    )}
                  </div>
                )
              })}
              {solution.steps && !solution.step_by_step && solution.steps.map((step, index) => {
                if (!step || step.trim() === '') return null
                
                const isHeader = step.startsWith('Problem') || (step.includes(':') && !step.startsWith('Step'))
                
                return (
                  <div
                    key={index}
                    className={`${
                      isHeader
                        ? 'bg-secondary/5 border-l-4 border-secondary p-4 rounded-r-lg'
                        : 'bg-muted/50 p-4 rounded-lg ml-4'
                    }`}
                  >
                    <div className={`${isHeader ? 'font-semibold text-secondary' : 'text-foreground/80'}`}>
                      {!isHeader && <span className="text-primary font-semibold mr-2">{index + 1}.</span>}
                      {cleanMarkdown(step)}
                    </div>
                  </div>
                )
              })}
            </div>
          </section>
        )}

        {/* Reasoning & Methodology Section */}
        {solution.reasoning && (
          <section className="bg-muted/30 rounded-lg p-6 border border-border">
            <div className="flex items-center space-x-2 mb-4">
              <Brain className="w-5 h-5 text-primary" />
              <h3 className="text-lg font-semibold text-foreground">Approach & Reasoning</h3>
            </div>
            <div className="prose prose-sm max-w-none text-foreground/80">
              <div className="whitespace-pre-wrap leading-relaxed">
                {cleanMarkdown(solution.reasoning)}
              </div>
            </div>
          </section>
        )}

        {/* Technical Details - Collapsible */}
        <section>
          <button
            onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
            className="flex items-center justify-between w-full p-4 bg-muted/50 hover:bg-muted rounded-lg transition-colors"
          >
            <div className="flex items-center space-x-2">
              <Settings className="w-5 h-5 text-muted-foreground" />
              <h3 className="text-sm font-semibold text-foreground">Technical Details</h3>
            </div>
            {showTechnicalDetails ? (
              <ChevronUp className="w-5 h-5 text-muted-foreground" />
            ) : (
              <ChevronDown className="w-5 h-5 text-muted-foreground" />
            )}
          </button>

          {showTechnicalDetails && (
            <div className="mt-3 p-4 bg-muted/30 rounded-lg border border-border animate-in">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground block mb-1">Model</span>
                  <span className="text-foreground font-medium">{solution.ai_model_used || solution.model_used}</span>
                </div>
                <div>
                  <span className="text-muted-foreground block mb-1">Confidence</span>
                  <span className="text-foreground font-medium">{Math.round((solution.confidence_score || 0) * 100)}%</span>
                </div>
                {solution.subject_area && (
                  <div>
                    <span className="text-muted-foreground block mb-1">Subject</span>
                    <span className="text-foreground font-medium">{solution.subject_area}</span>
                  </div>
                )}
                <div>
                  <span className="text-muted-foreground block mb-1">Processing Time</span>
                  <span className="text-foreground font-medium">{solution.processing_time || 0}s</span>
                </div>
                <div>
                  <span className="text-muted-foreground block mb-1">Generated</span>
                  <span className="text-foreground font-medium text-xs">{formatDate(solution.created_at || solution.generated_at)}</span>
                </div>
                <div>
                  <span className="text-muted-foreground block mb-1">Quality</span>
                  <span className={`font-medium ${solution.quality_validated ? 'text-green-600' : 'text-yellow-600'}`}>
                    {solution.quality_validated ? 'Validated' : 'Pending'}
                  </span>
                </div>
              </div>
            </div>
          )}
        </section>
      </div>

      {/* Feedback Section */}
      <div className="border-t border-border px-6 py-4 bg-muted/20">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-sm font-medium text-foreground">Rate this solution</h4>
            <p className="text-xs text-muted-foreground">Help us improve our AI-generated solutions</p>
          </div>
          <div className="flex items-center space-x-1">
            {[1, 2, 3, 4, 5].map((rating) => (
              <button
                key={rating}
                onClick={() => handleFeedbackRating(rating)}
                className={`p-1.5 rounded-lg hover:bg-muted transition-all transform hover:scale-110 ${
                  rating <= feedbackRating ? 'text-yellow-500' : 'text-muted-foreground'
                }`}
              >
                <Star className={`w-5 h-5 ${rating <= feedbackRating ? 'fill-current' : ''}`} />
              </button>
            ))}
            {feedbackRating > 0 && (
              <span className="ml-2 text-sm font-medium text-foreground">
                {feedbackRating}/5
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
