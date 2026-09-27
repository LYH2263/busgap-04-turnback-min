<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const rows = ref<any[]>([])
const edits = ref<Record<number, string>>({})
const saving = ref<number | null>(null)
async function load() {
  rows.value = await api('/lines')
  rows.value.forEach(r => { edits.value[r.id] = r.min_turnaround_min ?? '' })
}
onMounted(load)
async function save(r: any) {
  saving.value = r.id
  try {
    const raw = (edits.value[r.id] ?? '').toString().trim()
    await api(`/lines/${r.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ min_turnaround_min: raw === '' ? null : Number(raw) }),
    })
    await load()
  } finally { saving.value = null }
}
</script>
<template>
  <h1>线路</h1>
  <p class="sub">运营线路与串车 / 大间隔判定阈值 · 最小折返可编辑，留空表示未配置</p>
  <div class="card">
    <table>
      <thead><tr><th>编码</th><th>名称</th><th>计划间隔(分)</th><th>串车阈值</th><th>大间隔阈值</th><th>最小折返(分)</th><th></th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id ?? JSON.stringify(r)">
          <td>{{ r.code }}</td>
          <td>{{ r.name }}</td>
          <td>{{ r.planned_headway_min }}</td>
          <td>{{ r.bunch_threshold }}</td>
          <td>{{ r.large_threshold }}</td>
          <td>
            <input
              class="turn-input"
              type="number"
              min="0"
              step="0.5"
              v-model="edits[r.id]"
              placeholder="未配置"
              @keyup.enter="save(r)"
            />
          </td>
          <td><button class="btn" :disabled="saving === r.id" @click="save(r)">保存</button></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
