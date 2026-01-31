<!-- ==========================================================================
Scenario Builder Component
What-if scenario calculator for forecasts - exclude patterns to see impact
============================================================================ -->

<script setup lang="ts">
import type { RecurringPattern } from '~/types/recurring'
import type {
  CashFlowForecastResponse,
  ScenarioRequest,
} from '~/types/analytics'

// ---------------------------------------------------------------------------
// Props & Emits
// ---------------------------------------------------------------------------

const props = defineProps<{
  baselineForecast: CashFlowForecastResponse
  currency: string
}>()

const emit = defineEmits<{
  scenarioCalculated: [scenario: CashFlowForecastResponse | null]
}>()

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------

const { fetchPatterns } = useRecurringApi()
const { calculateScenario } = useAnalyticsApi()
const toast = useToastStore()

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

// Pattern data for selection
const patterns = ref<RecurringPattern[]>([])
const loadingPatterns = ref(true)

// Selected patterns to exclude
const excludedPatterns = ref<Set<string>>(new Set())

// Scenario calculation state
const scenarioData = ref<CashFlowForecastResponse | null>(null)
const calculating = ref(false)

// UI state - collapsed by default
const expanded = ref(false)

// ---------------------------------------------------------------------------
// Computed
// ---------------------------------------------------------------------------

// Only show active patterns (not paused or cancelled)
const activePatterns = computed(() =>
  patterns.value.filter(
    (p: RecurringPattern) => p.status === 'active' || p.status === 'pending',
  ),
)

// Separate expenses and income
const expensePatterns = computed(() =>
  activePatterns.value.filter(
    (p: RecurringPattern) => p.direction === 'expense',
  ),
)

const incomePatterns = computed(() =>
  activePatterns.value.filter(
    (p: RecurringPattern) => p.direction === 'income',
  ),
)

// Calculate total monthly impact of excluded patterns
const excludedMonthlyImpact = computed(() => {
  let impact = 0
  for (const patternId of excludedPatterns.value) {
    const pattern = patterns.value.find(
      (p: RecurringPattern) => p.id === patternId,
    )
    if (pattern) {
      // Monthly equivalent is always positive, direction tells us the sign
      impact +=
        pattern.direction === 'expense'
          ? pattern.monthly_equivalent
          : -pattern.monthly_equivalent
    }
  }
  return impact
})

// Compare baseline and scenario summaries
const comparison = computed(() => {
  if (!scenarioData.value) return null

  const baseline = props.baselineForecast.summary
  const scenario = scenarioData.value.summary

  const baselineEnd = parseFloat(baseline.ending_balance)
  const scenarioEnd = parseFloat(scenario.ending_balance)
  const difference = scenarioEnd - baselineEnd

  return {
    baselineEndBalance: baselineEnd,
    scenarioEndBalance: scenarioEnd,
    difference,
    percentChange:
      baselineEnd !== 0 ? (difference / Math.abs(baselineEnd)) * 100 : 0,
    baselineRunway: baseline.runway_days,
    scenarioRunway: scenario.runway_days,
  }
})

// ---------------------------------------------------------------------------
// Data Loading
// ---------------------------------------------------------------------------

async function loadPatterns() {
  loadingPatterns.value = true
  try {
    // Fetch active and pending patterns for scenario building
    const response = await fetchPatterns()
    patterns.value = response.patterns
  } catch {
    toast.error('Failed to load recurring patterns')
  } finally {
    loadingPatterns.value = false
  }
}

onMounted(() => {
  loadPatterns()
})

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

function togglePattern(patternId: string) {
  const newSet = new Set(excludedPatterns.value)
  if (newSet.has(patternId)) {
    newSet.delete(patternId)
  } else {
    newSet.add(patternId)
  }
  excludedPatterns.value = newSet

  // Clear previous scenario when selection changes
  scenarioData.value = null
  emit('scenarioCalculated', null)
}

async function calculateScenarioForecast() {
  if (excludedPatterns.value.size === 0) {
    toast.info('Select at least one pattern to exclude')
    return
  }

  calculating.value = true
  try {
    const request: ScenarioRequest = {
      exclude_patterns: Array.from(excludedPatterns.value),
    }
    scenarioData.value = await calculateScenario(request)
    emit('scenarioCalculated', scenarioData.value)
  } catch {
    toast.error('Failed to calculate scenario')
  } finally {
    calculating.value = false
  }
}

function clearScenario() {
  excludedPatterns.value = new Set()
  scenarioData.value = null
  emit('scenarioCalculated', null)
}

// ---------------------------------------------------------------------------
// Formatting
// ---------------------------------------------------------------------------

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: props.currency || 'GBP',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}
</script>

<template>
  <!-- Collapsible scenario builder panel -->
  <div class="rounded-lg border border-border bg-surface">
    <!-- Header - always visible, clickable to expand/collapse -->
    <button
      type="button"
      class="flex w-full items-center justify-between px-6 py-4 text-left hover:bg-border/10"
      @click="expanded = !expanded"
    >
      <div>
        <h2 class="text-lg font-semibold">What-If Scenario</h2>
        <p class="text-sm text-muted">
          Model the impact of cancelling subscriptions or stopping income
        </p>
      </div>
      <!-- Expand/collapse icon -->
      <svg
        :class="[
          'h-5 w-5 text-muted transition-transform',
          expanded && 'rotate-180',
        ]"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M19 9l-7 7-7-7"
        />
      </svg>
    </button>

    <!-- Expandable content -->
    <div v-if="expanded" class="border-t border-border px-6 py-4">
      <!-- Loading patterns -->
      <div v-if="loadingPatterns" class="py-4 text-center text-muted">
        Loading patterns...
      </div>

      <!-- No patterns state -->
      <div
        v-else-if="activePatterns.length === 0"
        class="py-4 text-center text-muted"
      >
        No recurring patterns found. Patterns are detected automatically from
        your transactions.
      </div>

      <!-- Pattern selection -->
      <div v-else class="space-y-4">
        <!-- Expenses section -->
        <div v-if="expensePatterns.length > 0">
          <h3 class="mb-2 text-sm font-medium text-muted">Expenses</h3>
          <div class="space-y-2">
            <label
              v-for="pattern in expensePatterns"
              :key="pattern.id"
              class="flex cursor-pointer items-center gap-3 rounded-lg border border-border p-3 transition-colors hover:bg-border/10"
              :class="
                excludedPatterns.has(pattern.id) &&
                'border-red-500/50 bg-red-500/10'
              "
            >
              <!-- Checkbox -->
              <input
                type="checkbox"
                :checked="excludedPatterns.has(pattern.id)"
                class="h-4 w-4 rounded border-border bg-background text-primary focus:ring-primary"
                @change="togglePattern(pattern.id)"
              />
              <!-- Pattern info -->
              <div class="flex-1">
                <span class="font-medium">{{ pattern.name }}</span>
                <span class="ml-2 text-sm text-muted">
                  {{
                    formatCurrency(Math.abs(pattern.monthly_equivalent))
                  }}/month
                </span>
              </div>
              <!-- Strike-through indicator when excluded -->
              <span
                v-if="excludedPatterns.has(pattern.id)"
                class="text-sm text-red-400"
              >
                Excluded
              </span>
            </label>
          </div>
        </div>

        <!-- Income section -->
        <div v-if="incomePatterns.length > 0">
          <h3 class="mb-2 text-sm font-medium text-muted">Income</h3>
          <div class="space-y-2">
            <label
              v-for="pattern in incomePatterns"
              :key="pattern.id"
              class="flex cursor-pointer items-center gap-3 rounded-lg border border-border p-3 transition-colors hover:bg-border/10"
              :class="
                excludedPatterns.has(pattern.id) &&
                'border-red-500/50 bg-red-500/10'
              "
            >
              <!-- Checkbox -->
              <input
                type="checkbox"
                :checked="excludedPatterns.has(pattern.id)"
                class="h-4 w-4 rounded border-border bg-background text-primary focus:ring-primary"
                @change="togglePattern(pattern.id)"
              />
              <!-- Pattern info -->
              <div class="flex-1">
                <span class="font-medium">{{ pattern.name }}</span>
                <span class="text-emerald-400 ml-2 text-sm">
                  +{{
                    formatCurrency(Math.abs(pattern.monthly_equivalent))
                  }}/month
                </span>
              </div>
              <!-- Strike-through indicator when excluded -->
              <span
                v-if="excludedPatterns.has(pattern.id)"
                class="text-sm text-red-400"
              >
                Excluded
              </span>
            </label>
          </div>
        </div>

        <!-- Monthly impact summary -->
        <div
          v-if="excludedPatterns.size > 0"
          class="rounded-lg border border-border bg-background p-4"
        >
          <div class="flex items-center justify-between">
            <span class="text-sm text-muted">Monthly Savings</span>
            <span
              :class="[
                'text-lg font-semibold',
                excludedMonthlyImpact > 0 ? 'text-emerald-400' : 'text-red-400',
              ]"
            >
              {{ excludedMonthlyImpact > 0 ? '+' : ''
              }}{{ formatCurrency(excludedMonthlyImpact) }}
            </span>
          </div>
        </div>

        <!-- Action buttons -->
        <div class="flex gap-3">
          <AppButton
            :disabled="excludedPatterns.size === 0 || calculating"
            :loading="calculating"
            class="flex-1"
            @click="calculateScenarioForecast"
          >
            Calculate Scenario
          </AppButton>
          <AppButton
            v-if="excludedPatterns.size > 0"
            variant="outline"
            @click="clearScenario"
          >
            Clear
          </AppButton>
        </div>

        <!-- Comparison results -->
        <div
          v-if="comparison"
          class="rounded-lg border border-primary/30 bg-primary/10 p-4"
        >
          <h3 class="mb-3 font-semibold">Scenario Impact (90 Days)</h3>

          <div class="grid gap-4 sm:grid-cols-3">
            <!-- Baseline -->
            <div>
              <p class="text-sm text-muted">Current Forecast</p>
              <p class="text-lg font-semibold">
                {{ formatCurrency(comparison.baselineEndBalance) }}
              </p>
            </div>

            <!-- Scenario -->
            <div>
              <p class="text-sm text-muted">With Changes</p>
              <p class="text-lg font-semibold">
                {{ formatCurrency(comparison.scenarioEndBalance) }}
              </p>
            </div>

            <!-- Difference -->
            <div>
              <p class="text-sm text-muted">Difference</p>
              <p
                :class="[
                  'text-lg font-semibold',
                  comparison.difference >= 0
                    ? 'text-emerald-400'
                    : 'text-red-400',
                ]"
              >
                {{ comparison.difference >= 0 ? '+' : ''
                }}{{ formatCurrency(comparison.difference) }}
                <span class="text-sm font-normal">
                  ({{ comparison.percentChange >= 0 ? '+' : ''
                  }}{{ comparison.percentChange.toFixed(1) }}%)
                </span>
              </p>
            </div>
          </div>

          <!-- Runway comparison if relevant -->
          <div
            v-if="
              comparison.baselineRunway !== null ||
              comparison.scenarioRunway !== null
            "
            class="mt-3 border-t border-border/50 pt-3"
          >
            <div class="flex items-center gap-4 text-sm">
              <span class="text-muted">Runway:</span>
              <span>
                Current:
                {{
                  comparison.baselineRunway !== null
                    ? `${comparison.baselineRunway} days`
                    : 'Healthy'
                }}
              </span>
              <span class="text-muted">→</span>
              <span
                :class="
                  comparison.scenarioRunway === null ||
                  (comparison.baselineRunway !== null &&
                    comparison.scenarioRunway > comparison.baselineRunway)
                    ? 'text-emerald-400'
                    : 'text-red-400'
                "
              >
                Scenario:
                {{
                  comparison.scenarioRunway !== null
                    ? `${comparison.scenarioRunway} days`
                    : 'Healthy'
                }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
