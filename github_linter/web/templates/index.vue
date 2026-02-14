{% extends "basetemplate.html" %}


{% block content %}


<h1>Repositories (|totalRepos|)</h1>
<label for="firstname">Search
  <input id="repofilter" placeholder="Filter Repos" type="text" v-model="repo_filter" /></label>

<div class="buttonbar">
<a href="#" id="update_repos" v-on:click="updateReposBackend" role="button"  :class="{ outline: !waiting_for_update }">
  <span v-if="waiting_for_update">Updating...</span><span v-else>Update Repositories</span></a>
<a href="#" id="hide_archived" @click="hide_archived = !hide_archived" role="button"  :class="{ outline: !hide_archived }">Hide archived</a>
<a href="#" id="show_has_issues" @click="show_has_issues = !show_has_issues" role="button"  :class="{ outline: !show_has_issues }" >With open issues</a>
<a href="#" id="show_has_prs" @click="show_has_prs = !show_has_prs" role="button"  :class="{ outline: !show_has_prs }" >With open PRs</a>
</div>
<table>
<thead>
  <tr>
    <th scope="col">Name</th>
    <th>&nbsp;</th>
    <th scope="col"></th>
    <th scope="col">Open Issues <span id="totalIssues">(| totalFilteredOpenIssues |)</span></th>
    <th scope="col">PRs <span id="totalFilteredPRs">(| totalFilteredPRs |)</span></th>
  </tr>
</thead>
<tbody>
<tr v-for="(repo, index) in filteredRows" :key="`repo-${repo.full_name}`">
  <th scope="row">| repo.full_name | <span v-if="repo.private">(P)</span></th>
  <td>
    <a :href="'https://github.com/'+repo.full_name" target="_blank">
      <img src="/images/open-black.svg" class="open" :aria-label="`Open ${repo.full_name} on GitHub`" :alt="`Open ${repo.full_name} on GitHub`" />
    </a>
  </td>
  <td v-if="repo.archived == 1"><span role="img" aria-label="Archived">🪦</span></td><td v-else></td>
  <td>
    <!-- https://renatello.com/vue-js-href/ -->
    <a v-if="repo.open_issues > 0" :href="`https://github.com/${repo.full_name}/issues`" target="_blank">|repo.open_issues|</a>
  </td>
  <td>
    <a v-if="repo.open_prs > 0" :href="`https://github.com/${repo.full_name}/pulls`" target="_blank">|repo.open_prs|</a>
  </td>
</tr>
</tbody>
</table>
</div>

{% endblock content %}