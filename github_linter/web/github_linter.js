// axios get from here: https://reactgo.com/vue-fetch-data/

// Vue.component('repo-item', {
//   props: ['repo'],
//   template: '<tr><th scope="row">{{ repo.full_name }}</th><td>{{repo.archived }}</td></tr>'
// })

const _repo_app = new Vue({
	delimiters: ["|", "|"], // because we're using it alongside jinja2
	el: "#repos",
	data: {
		repos: [{ full_name: "Loading" }],
		repo_filter: "",
		hide_archived: false,
		show_has_issues: true,
		show_has_prs: false,
		last_updated: null,
		waiting_for_update: false, // used when waiting for repos to update
		// total_issues: -1,
	},
	created() {
		this.updateRepos();
		this.getLastUpdated();
		this.timer = setInterval(this.getLastUpdated, 5000);
		this.timer = setInterval(this.updateRepos, 5000);
		this.timer = setInterval(this.checkIsWaiting, 1000);
	},
	computed: {
		filteredRows() {
			return this.repos.filter((repo) => {
				const full_name = repo.full_name.toString().toLowerCase();
				let owner = "";
				if (typeof repo.owner !== "undefined" && repo.owner != null) {
					owner = repo.owner.toString().toLowerCase();
				}
				// const department = repo.department.toLowerCase();
				const searchTerm = this.repo_filter.toLowerCase();
				let result =
					full_name.includes(searchTerm) || owner.includes(searchTerm);

				// filter for show_has_issues
				if (this.show_has_issues && result) {
					if (repo.open_issues === 0) {
						result = false;
						// console.log("hiding " + repo.full_name + " because it doesn't have issues");
					}
				}
				// filter for show_has_prs
				if (this.show_has_prs && result) {
					if (repo.open_prs === 0) {
						result = false;
					} else {
						result = true;
					}
				}
				// filter for hide_archived
				if (this.hide_archived && result) {
					if (repo.archived === true) {
						// console.log("skipping archived" + repo.full_name);
						result = false;
					}
				}

				return result;
			});
		},
		totalRepos() {
			// this calculates the current view's number of total open issues
			return this.filteredRows.length;
		},
		totalFilteredOpenIssues() {
			// this calculates the current view's number of total open issues
			tmp_count = 0;
			for (const issue of this.filteredRows) {
				tmp_count += issue.open_issues;
				// console.log("issues: "+issue.open_issues)
			}
			return tmp_count;
		},
		totalFilteredPRs() {
			// this calculates the current view's number of total open issues
			tmp_count = 0;
			for (const issue of this.filteredRows) {
				tmp_count += issue.open_prs;
			}
			return tmp_count;
		},
	},
	methods: {
		updateRepos: function () {
			const headers = { crossDomain: true };
			axios.get("/repos", headers).then((res) => {
				this.repos = res.data;
			});
			// TODO: maybe block the update repos button for 30 seconds?
		},
		getLastUpdated: function () {
			// get the "last updated" data
			axios.get("/db/updated").then((res) => {
				if (res.data > this.last_updated) {
					this.waiting_for_update = false;
					this.last_updated = res.data;
				} else {
					console.log(
						`result: ${res.data} less than or equal to ${this.last_updated}`,
					);
				}
			});
		},
		updateReposBackend: function () {
			this.waiting_for_update = true;
			axios.get("/repos/update");
		},
		checkIsWaiting: function () {
			axios.get("/db/updating").then((res) => {
				this.waiting_for_update = res.data;
			});
		},
	},
});
