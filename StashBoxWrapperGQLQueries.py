GET_PERFORMER = """
query Query($input: ID!) {
    findPerformer(id: $input) {
        ... PerformerFragment
    }
}
"""

GET_PERFORMER_EDITS = """
query QueryEdits($input: EditQueryInput!) {
  queryEdits(input: $input) {
    count
    edits {
      applied
      details {
        ... PerformerEditFragment
      }
      id
      merge_sources {
        ... PerformerFragment
      }
      old_details {
        ... PerformerEditFragment
      }
      operation
      options {
        set_merge_aliases
        set_modify_aliases
      }
      status
      target {
        ... PerformerFragment
      }
      updated
      closed
    }
  }
}
"""

GET_ALL_PERFORMERS = """
query QueryPerformers($input: PerformerQueryInput!) {
    queryPerformers(input: $input) {
        count
        performers {
        ... PerformerFragmentWidthEdits
        }
    }
}
"""

GET_ALL_PERFORMER_EDITS = """
    query QueryEdits($input: EditQueryInput!) {
  queryEdits(input: $input) {
    edits {
      applied
      closed
      details {
        ... PerformerEditFragment
      }
      id
      status
      operation
      target {
        ... PerformerFragment
      }
        merge_sources {
        ... on Performer {
          id
        }
      }
    }
    count
  }
}
"""


FRAG_PERF = """
fragment PerformerFragment on Performer {
  aliases
  band_size
  breast_type
  career_end_year
  career_start_year
  country
  cup_size
  disambiguation
  ethnicity
  eye_color
  gender
  hair_color
  height
  hip_size
  images {
    id
    url
  }
  name
  piercings {
    location
    description
  }
  tattoos {
    description
    location
  }
  urls {
    site {
      id
    }
    url
  }
  waist_size
  age
  id
  merged_ids
  birth_date
  birthdate {
    date
  }
  created
  updated
  deleted
}
"""


FRAG_PERFEDIT = """
fragment PerformerEditFragment on PerformerEdit {
  added_aliases
  added_images {
    id
    url
  }
  added_piercings {
    location
    description
  }
  added_tattoos {
    location
    description
  }
  added_urls {
    site {
      id
    }
    url
  }
  aliases
  band_size
  birthdate
  breast_type
  career_end_year
  career_start_year
  country
  cup_size
  disambiguation
  draft_id
  ethnicity
  eye_color
  gender
  hair_color
  height
  hip_size
  images {
    id
    url
  }
  name
  piercings {
    location
    description
  }
  removed_aliases
  removed_images {
    id
    url
  }
  removed_piercings {
    description
    location
  }
  removed_tattoos {
    description
    location
  }
  removed_urls {
    site {
      id
    }
    url
  }
  tattoos {
    description
    location
  }
  urls {
    site {
      id
    }
    url
  }
  waist_size
}
"""

FRAG_PERF_WITH_EDITS = """
fragment PerformerFragmentWidthEdits on Performer {
  ... PerformerFragment
  edits {
    applied
      details {
        ... PerformerEditFragment
      }
      id
      merge_sources {
        ... PerformerFragment
      }
      old_details {
        ... PerformerEditFragment
      }
      operation
      options {
        set_merge_aliases
        set_modify_aliases
      }
      status
      target {
        ... PerformerFragment
      }
      updated
      closed
  }
}
"""

FRAGMENTS = {
    "PerformerFragment" : FRAG_PERF,
    "PerformerEditFragment" : FRAG_PERFEDIT,
    "PerformerFragmentWidthEdits" : FRAG_PERF_WITH_EDITS
}




