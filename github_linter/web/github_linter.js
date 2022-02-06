
// axios get from here: https://reactgo.com/vue-fetch-data/

// Vue.component('repo-item', {
//   props: ['repo'],
//   template: '<tr><th scope="row">{{ repo.full_name }}</th><td>{{repo.archived }}</td></tr>'
// })

var repo_app = new Vue({
    el: '#repos',
    data: {
      repos: [
        { full_name: "Loading" }
      ],
      repo_filter:'',
      show_only_archived: false,
    },
    created () {
      this.updateRepos();
      this.timer = setInterval(this.updateRepos, 5000);

    },
    computed: {
      filteredRows() {
        return this.repos.filter(repo => {
          var full_name = repo.full_name.toString().toLowerCase();
          var owner = "";
          if ( typeof repo.owner != 'undefined' && repo.owner != null ) {
            owner = repo.owner.toString().toLowerCase();
          }
          // const department = repo.department.toLowerCase();
          const searchTerm = this.repo_filter.toLowerCase();

          return full_name.includes(searchTerm) || owner.includes(searchTerm);

          });
        }
    },
    methods: {

      updateRepos: function() {
        axios
        .get("/repos")
        .then(res => {
          this.repos = res.data;
        });
        // TODO: maybe block the update repos button for 30 seconds?
      },
      updateReposBackend: function () {
        axios.get("/repos/update");
      }
    }
  })

