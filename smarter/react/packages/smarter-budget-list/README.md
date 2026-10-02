# Smarter Budgets List React App

This is the source code for the Budgets List app located
at [http://localhost:9357/budget/](http://localhost:9357/budget/).

It lists the budgets that the user may see. Each budget expands to the resources it is attached
to, with their budget versus actual spending this billing period and in total, and a chart of the
last 12 billing periods. Superusers may delete a budget. Budgets are created and changed with
Budget manifests: `smarter apply -f budget.yaml`.

This component is served by Django. See also:

- [smarter.apps.account.views.budget.listview.BudgetListView](../../../smarter/apps/account/views/budget/listview.py)
- [smarter.apps.account.templatetags.react_budget_list.budget_list_react_assets](../../../smarter/apps/account/templatetags/react_budget_list.py)
- [templates/react/budget-list.html](../../../smarter/templates/react/budget-list.html)

## Setup

```console
npm install
npm run dev     # http://localhost:5173, with API requests proxied to Django on :9357
npm run build   # builds into smarter/static/react/@smarter/budget-list/
```
